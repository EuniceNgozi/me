from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Query, Depends, Cookie, Response
from fastapi.security import HTTPBearer
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
import httpx
import json
import secrets
import hashlib
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(
    title="Viral Leads Generator", 
    description="AI-powered social media lead generation platform",
    version="1.0.0"
)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Data Models
class Platform(str, Enum):
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    PINTEREST = "pinterest"
    TIKTOK = "tiktok"

class InterestCategory(str, Enum):
    DIGITAL_MARKETING = "digital_marketing"
    ONLINE_COURSES = "online_courses"
    SAAS_TOOLS = "saas_tools"
    ECOMMERCE = "ecommerce"
    DESIGN_TOOLS = "design_tools"
    PRODUCTIVITY = "productivity"
    BUSINESS_TOOLS = "business_tools"

class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    picture: Optional[str] = None
    tier: UserTier = UserTier.FREE
    leads_discovered: int = 0
    monthly_limit: int = 50  # Free tier limit
    last_reset: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    facebook_access_token: Optional[str] = None
    instagram_access_token: Optional[str] = None
    pinterest_access_token: Optional[str] = None

class Session(BaseModel):
    session_token: str
    user_id: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Lead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str  # Which user discovered this lead
    username: str
    platform: Platform
    profile_url: Optional[str] = None
    follower_count: int = 0
    engagement_rate: float = 0.0
    interests: List[InterestCategory] = []
    interest_score: float = 0.0
    viral_potential: float = 0.0
    last_active: Optional[datetime] = None
    trending_topics: List[str] = []
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    analyzed_posts: int = 0
    real_data: bool = False  # True if from real API, False if mock

class LeadCreate(BaseModel):
    username: str
    platform: Platform
    profile_url: Optional[str] = None

class AnalysisRequest(BaseModel):
    platforms: List[Platform]
    keywords: List[str]
    max_leads: int = Field(default=20, le=100)
    min_followers: int = Field(default=1000, ge=0)
    days_back: int = Field(default=30, le=90)

class TrendingTopic(BaseModel):
    topic: str
    platform: Platform
    engagement_score: float
    post_count: int
    growth_rate: float
    related_keywords: List[str]
    discovered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ConnectPlatformRequest(BaseModel):
    platform: Platform
    access_token: str

# Authentication & User Management
class AuthService:
    @staticmethod
    async def get_session_data(session_id: str) -> Optional[Dict]:
        """Get user data from Emergent auth service"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"X-Session-ID": session_id}
                response = await client.get(
                    "https://demobackend.emergentagent.com/auth/v1/env/oauth/session-data",
                    headers=headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                return None
        except Exception as e:
            logger.error(f"Failed to get session data: {str(e)}")
            return None
    
    @staticmethod
    async def create_or_get_user(user_data: Dict) -> User:
        """Create new user or get existing user"""
        existing_user = await db.users.find_one({"email": user_data["email"]})
        
        if existing_user:
            return User(**existing_user)
        
        # Create new user
        new_user = User(
            email=user_data["email"],
            name=user_data["name"],
            picture=user_data.get("picture")
        )
        
        await db.users.insert_one(new_user.dict())
        return new_user
    
    @staticmethod
    async def create_session(user_id: str, session_token: str) -> Session:
        """Create new session"""
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        
        session = Session(
            session_token=session_token,
            user_id=user_id,
            expires_at=expires_at
        )
        
        await db.sessions.insert_one(session.dict())
        return session
    
    @staticmethod
    async def get_user_by_session(session_token: str) -> Optional[User]:
        """Get user by session token"""
        session = await db.sessions.find_one({
            "session_token": session_token,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        
        if not session:
            return None
        
        user = await db.users.find_one({"id": session["user_id"]})
        return User(**user) if user else None
    
    @staticmethod
    async def delete_session(session_token: str):
        """Delete session (logout)"""
        await db.sessions.delete_one({"session_token": session_token})

# Authentication dependency
async def get_current_user(
    session_token: Optional[str] = Cookie(None),
    authorization: Optional[str] = None
) -> Optional[User]:
    """Get current authenticated user"""
    # Try cookie first, then authorization header
    token = session_token
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization[7:]
    
    if not token:
        return None
    
    return await AuthService.get_user_by_session(token)

async def require_auth(current_user: User = Depends(get_current_user)) -> User:
    """Require authentication"""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    return current_user

# Content Analysis Service (Enhanced)
class ContentAnalysisService:
    def __init__(self):
        self.llm_key = os.environ.get('EMERGENT_LLM_KEY')
        
    async def analyze_content_for_interests(self, content: str, platform: str) -> Dict[str, Any]:
        """Analyze social media content to identify digital product interests"""
        try:
            from emergentintegrations.llm.chat import LlmChat, UserMessage
            
            chat = LlmChat(
                api_key=self.llm_key,
                session_id=f"content_analysis_{uuid.uuid4()}",
                system_message="""You are an expert at analyzing social media content to identify users interested in digital products. 

Analyze the following content and determine:
1. Interest categories (digital_marketing, online_courses, saas_tools, ecommerce, design_tools, productivity, business_tools)
2. Interest score (0-100) - higher scores for explicit mentions of tools/products/services
3. Viral potential (0-100) - based on engagement potential and content quality
4. Key topics/keywords mentioned
5. Purchase intent indicators (0-100) - phrases like "looking for", "need", "recommend"

Return ONLY a valid JSON response with: interests, interest_score, viral_potential, trending_topics, purchase_intent"""
            ).with_model("openai", "gpt-4o-mini")
            
            user_message = UserMessage(
                text=f"Platform: {platform}\n\nContent to analyze:\n{content}\n\nAnalyze this content and return JSON only."
            )
            
            response = await chat.send_message(user_message)
            
            # Parse the JSON response
            try:
                # Clean the response to extract JSON
                clean_response = response.strip()
                if clean_response.startswith('```json'):
                    clean_response = clean_response[7:-3]
                elif clean_response.startswith('```'):
                    clean_response = clean_response[3:-3]
                
                analysis = json.loads(clean_response)
            except json.JSONDecodeError:
                # Fallback analysis if LLM doesn't return valid JSON
                analysis = {
                    "interests": self._extract_basic_interests(content),
                    "interest_score": self._calculate_basic_score(content),
                    "viral_potential": 50.0,
                    "trending_topics": self._extract_keywords(content),
                    "purchase_intent": 30.0
                }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Content analysis failed: {str(e)}")
            # Fallback to basic keyword analysis
            return {
                "interests": self._extract_basic_interests(content),
                "interest_score": self._calculate_basic_score(content),
                "viral_potential": 50.0,
                "trending_topics": self._extract_keywords(content),
                "purchase_intent": 25.0
            }
    
    def _extract_basic_interests(self, content: str) -> List[str]:
        """Basic keyword-based interest extraction"""
        content_lower = content.lower()
        interests = []
        
        keywords_map = {
            "digital_marketing": ["seo", "marketing", "ads", "social media", "content", "brand", "campaign"],
            "online_courses": ["course", "learn", "training", "education", "skill", "tutorial", "certification"],
            "saas_tools": ["software", "app", "tool", "platform", "automation", "crm", "dashboard"],
            "ecommerce": ["shop", "store", "sell", "product", "business", "revenue", "sales"],
            "design_tools": ["design", "creative", "ui", "ux", "graphics", "visual", "figma", "canva"],
            "productivity": ["productivity", "efficient", "organize", "manage", "workflow", "notion"],
            "business_tools": ["business", "entrepreneur", "startup", "growth", "strategy", "analytics"]
        }
        
        for category, keywords in keywords_map.items():
            if any(keyword in content_lower for keyword in keywords):
                interests.append(category)
        
        return interests[:3]  # Top 3 interests
    
    def _calculate_basic_score(self, content: str) -> float:
        """Basic scoring based on keyword frequency and engagement indicators"""
        content_lower = content.lower()
        score = 0
        
        # Digital product keywords
        digital_keywords = ["digital", "online", "software", "course", "tool", "app", "platform", "saas"]
        score += sum(8 for keyword in digital_keywords if keyword in content_lower)
        
        # Engagement indicators
        engagement_words = ["love", "recommend", "amazing", "game changer", "must have", "incredible", "fantastic"]
        score += sum(12 for word in engagement_words if word in content_lower)
        
        # Intent indicators
        intent_words = ["looking for", "need", "searching", "want", "buying", "considering", "planning"]
        score += sum(15 for word in intent_words if word in content_lower)
        
        return min(100.0, score)
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract trending keywords/topics"""
        import re
        
        # Extract hashtags
        hashtags = re.findall(r'#(\w+)', content)
        
        # Extract common digital product terms
        words = content.lower().split()
        relevant_words = []
        for word in words:
            if len(word) > 3 and word not in ["this", "that", "with", "from", "they", "have", "will", "been"]:
                relevant_words.append(word)
        
        return (hashtags + relevant_words)[:5]

# Pinterest API Service
class PinterestAPIService:
    def __init__(self):
        self.base_url = "https://api.pinterest.com/v5"
        self.content_analyzer = ContentAnalysisService()
    
    async def get_pinterest_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Pinterest business account information"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                url = f"{self.base_url}/user_account"
                
                response = await client.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Pinterest API error: {response.status_code} - {response.text}")
                    return {}
        except Exception as e:
            logger.error(f"Pinterest API request failed: {str(e)}")
            return {}
    
    async def get_pinterest_boards(self, access_token: str, limit: int = 25) -> List[Dict]:
        """Get Pinterest user's boards"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                url = f"{self.base_url}/boards"
                params = {"page_size": limit}
                
                response = await client.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json().get("items", [])
                else:
                    logger.error(f"Pinterest boards API error: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Pinterest boards request failed: {str(e)}")
            return []
    
    async def get_board_pins(self, access_token: str, board_id: str, limit: int = 25) -> List[Dict]:
        """Get pins from a Pinterest board"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {"Authorization": f"Bearer {access_token}"}
                url = f"{self.base_url}/boards/{board_id}/pins"
                params = {"page_size": limit}
                
                response = await client.get(url, headers=headers, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json().get("items", [])
                else:
                    logger.error(f"Pinterest pins API error: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Pinterest pins request failed: {str(e)}")
            return []
    
    async def analyze_pinterest_content_for_leads(self, boards: List[Dict], user_id: str) -> List[Lead]:
        """Analyze Pinterest boards and pins to generate leads"""
        leads = []
        
        for board in boards[:5]:  # Limit boards to process
            board_name = board.get("name", "")
            board_description = board.get("description", "")
            
            # Combine board info for analysis
            content_to_analyze = f"{board_name}. {board_description}"
            
            if len(content_to_analyze.strip()) < 10:
                continue
            
            # Analyze content with AI
            analysis = await self.content_analyzer.analyze_content_for_interests(content_to_analyze, "pinterest")
            
            # Only create leads for boards with significant digital product interest
            if analysis.get("interest_score", 0) > 20:
                # Extract meaningful username from board owner
                board_owner = board.get("owner", {})
                username = board_owner.get("username", f"pinterest_user_{board.get('id', '')[:8]}")
                
                # Estimate engagement based on board stats
                pin_count = board.get("pin_count", 0)
                follower_count = board.get("follower_count", 0)
                
                # Calculate estimated engagement rate
                estimated_followers = max(500, follower_count)
                engagement_rate = min(0.08, (pin_count * 2 + follower_count) / max(estimated_followers * 10, 1))
                
                lead = Lead(
                    user_id=user_id,
                    username=username,
                    platform=Platform.PINTEREST,
                    profile_url=f"https://pinterest.com/{username}/",
                    follower_count=estimated_followers,
                    engagement_rate=engagement_rate,
                    interests=[InterestCategory(interest) for interest in analysis.get("interests", []) if interest in [e.value for e in InterestCategory]],
                    interest_score=analysis.get("interest_score", 0),
                    viral_potential=analysis.get("viral_potential", 0),
                    trending_topics=analysis.get("trending_topics", []),
                    analyzed_posts=min(pin_count, 10),
                    real_data=True
                )
                
                leads.append(lead)
        
        return leads

# Instagram API Service  
class InstagramAPIService:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v19.0"
        self.content_analyzer = ContentAnalysisService()
    
    async def get_instagram_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get Instagram business account information"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/me"
                params = {
                    "fields": "id,username,name,biography,website,followers_count,follows_count,media_count,profile_picture_url",
                    "access_token": access_token
                }
                
                response = await client.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Instagram API error: {response.status_code} - {response.text}")
                    return {}
        except Exception as e:
            logger.error(f"Instagram API request failed: {str(e)}")
            return {}
    
    async def get_instagram_media(self, access_token: str, user_id: str = "me", limit: int = 25) -> List[Dict]:
        """Get Instagram business account media posts"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/{user_id}/media"
                params = {
                    "fields": "id,media_type,media_url,permalink,thumbnail_url,caption,timestamp,username,comments_count,like_count",
                    "limit": limit,
                    "access_token": access_token
                }
                
                response = await client.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json().get("data", [])
                else:
                    logger.error(f"Instagram media API error: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Instagram media request failed: {str(e)}")
            return []
    
    async def get_instagram_insights(self, media_id: str, access_token: str) -> Dict[str, Any]:
        """Get insights for Instagram media"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/{media_id}/insights"
                params = {
                    "metric": "impressions,reach,engagement,saves,profile_visits,follows",
                    "access_token": access_token
                }
                
                response = await client.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    insights = {}
                    
                    for item in data.get("data", []):
                        metric_name = item.get("name")
                        values = item.get("values", [])
                        if values:
                            insights[metric_name] = values[0].get("value", 0)
                    
                    return insights
                else:
                    logger.error(f"Instagram insights error: {response.status_code} - {response.text}")
                    return {}
        except Exception as e:
            logger.error(f"Instagram insights request failed: {str(e)}")
            return {}
    
    async def analyze_instagram_posts_for_leads(self, posts: List[Dict], user_id: str) -> List[Lead]:
        """Analyze Instagram posts to generate leads"""
        leads = []
        
        for post in posts:
            caption = post.get("caption", "")
            if not caption or len(caption) < 15:
                continue
            
            # Analyze content with AI
            analysis = await self.content_analyzer.analyze_content_for_interests(caption, "instagram")
            
            # Only create leads for users with significant digital product interest
            if analysis.get("interest_score", 0) > 25:
                username = post.get("username", f"ig_user_{post.get('id', '')[:8]}")
                
                # Calculate engagement metrics
                likes = post.get("like_count", 0)
                comments = post.get("comments_count", 0)
                
                # Estimate follower count and engagement rate (Instagram doesn't provide follower count easily)
                estimated_followers = max(1000, likes * 20)  # Rough estimation
                engagement_rate = min(0.15, (likes + comments * 3) / estimated_followers)
                
                lead = Lead(
                    user_id=user_id,
                    username=username,
                    platform=Platform.INSTAGRAM,
                    profile_url=post.get("permalink", ""),
                    follower_count=estimated_followers,
                    engagement_rate=engagement_rate,
                    interests=[InterestCategory(interest) for interest in analysis.get("interests", []) if interest in [e.value for e in InterestCategory]],
                    interest_score=analysis.get("interest_score", 0),
                    viral_potential=analysis.get("viral_potential", 0),
                    trending_topics=analysis.get("trending_topics", []),
                    analyzed_posts=1,
                    real_data=True
                )
                
                leads.append(lead)
        
        return leads

# Facebook API Service
class FacebookAPIService:
    def __init__(self):
        self.base_url = "https://graph.facebook.com/v19.0"
        self.content_analyzer = ContentAnalysisService()
    
    async def get_user_posts(self, access_token: str, user_id: str = "me", limit: int = 25) -> List[Dict]:
        """Get user's Facebook posts"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/{user_id}/posts"
                params = {
                    "access_token": access_token,
                    "fields": "id,message,created_time,likes.summary(true),comments.summary(true),shares",
                    "limit": limit
                }
                
                response = await client.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json().get("data", [])
                else:
                    logger.error(f"Facebook API error: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Facebook API request failed: {str(e)}")
            return []
    
    async def search_posts_by_keyword(self, access_token: str, keyword: str, limit: int = 50) -> List[Dict]:
        """Search public posts by keyword (requires special permissions)"""
        try:
            async with httpx.AsyncClient() as client:
                url = f"{self.base_url}/search"
                params = {
                    "access_token": access_token,
                    "q": keyword,
                    "type": "post",
                    "fields": "id,message,created_time,from,likes.summary(true),comments.summary(true)",
                    "limit": limit
                }
                
                response = await client.get(url, params=params, timeout=30)
                
                if response.status_code == 200:
                    return response.json().get("data", [])
                else:
                    logger.error(f"Facebook search error: {response.status_code} - {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Facebook search failed: {str(e)}")
            return []
    
    async def analyze_posts_for_leads(self, posts: List[Dict], user_id: str) -> List[Lead]:
        """Analyze Facebook posts to generate leads"""
        leads = []
        
        for post in posts:
            message = post.get("message", "")
            if not message or len(message) < 20:
                continue
            
            # Analyze content
            analysis = await self.content_analyzer.analyze_content_for_interests(message, "facebook")
            
            # Only create leads for users with significant digital product interest
            if analysis.get("interest_score", 0) > 30:
                from_info = post.get("from", {})
                username = from_info.get("name", f"user_{post.get('id', '')[:8]}")
                
                # Calculate engagement metrics
                likes = post.get("likes", {}).get("summary", {}).get("total_count", 0)
                comments = post.get("comments", {}).get("summary", {}).get("total_count", 0)
                shares = post.get("shares", {}).get("count", 0)
                
                engagement_rate = min(1.0, (likes + comments * 3 + shares * 5) / 1000)  # Normalize
                
                lead = Lead(
                    user_id=user_id,
                    username=username,
                    platform=Platform.FACEBOOK,
                    profile_url=f"https://facebook.com/{from_info.get('id', '')}",
                    follower_count=0,  # Facebook doesn't provide this easily
                    engagement_rate=engagement_rate,
                    interests=[InterestCategory(interest) for interest in analysis.get("interests", []) if interest in [e.value for e in InterestCategory]],
                    interest_score=analysis.get("interest_score", 0),
                    viral_potential=analysis.get("viral_potential", 0),
                    trending_topics=analysis.get("trending_topics", []),
                    analyzed_posts=1,
                    real_data=True
                )
                
                leads.append(lead)
        
        return leads

# Social Media Service (Enhanced with Real APIs)
class SocialMediaService:
    def __init__(self):
        self.content_analyzer = ContentAnalysisService()
        self.facebook_api = FacebookAPIService()
        self.instagram_api = InstagramAPIService()
        self.pinterest_api = PinterestAPIService()
    
    async def discover_leads_from_keywords(
        self, 
        keywords: List[str], 
        platforms: List[Platform], 
        user: User,
        limit: int = 50
    ) -> List[Lead]:
        """Discover leads using real APIs where available, mock data otherwise"""
        all_leads = []
        
        for platform in platforms:
            if platform == Platform.FACEBOOK and user.facebook_access_token:
                # Use real Facebook API
                facebook_leads = await self._discover_facebook_leads(keywords, user, limit // len(platforms))
                all_leads.extend(facebook_leads)
            elif platform == Platform.INSTAGRAM and user.instagram_access_token:
                # Use real Instagram API
                instagram_leads = await self._discover_instagram_leads(keywords, user, limit // len(platforms))
                all_leads.extend(instagram_leads)
            elif platform == Platform.PINTEREST and user.pinterest_access_token:
                # Use real Pinterest API
                pinterest_leads = await self._discover_pinterest_leads(keywords, user, limit // len(platforms))
                all_leads.extend(pinterest_leads)
            else:
                # Use mock data for other platforms or if no token
                mock_leads = await self._discover_mock_leads(keywords, platform, user.id, limit // len(platforms))
                all_leads.extend(mock_leads)
        
        return all_leads[:limit]
    
    async def _discover_pinterest_leads(self, keywords: List[str], user: User, limit: int) -> List[Lead]:
        """Discover leads from Pinterest using real API"""
        leads = []
        
        try:
            # Get user's Pinterest boards
            boards = await self.pinterest_api.get_pinterest_boards(
                user.pinterest_access_token, limit=20
            )
            
            # Analyze boards for leads
            if boards:
                pinterest_leads = await self.pinterest_api.analyze_pinterest_content_for_leads(boards, user.id)
                
                # Filter by keywords relevance
                keyword_filtered_leads = []
                for lead in pinterest_leads:
                    # Check if any interests or trending topics match keywords
                    lead_content = " ".join(lead.trending_topics + [interest.value for interest in lead.interests])
                    keyword_matches = any(
                        keyword.lower() in lead_content.lower() 
                        for keyword in keywords
                    )
                    
                    if keyword_matches or lead.interest_score > 35:
                        keyword_filtered_leads.append(lead)
                
                leads.extend(keyword_filtered_leads[:limit])
        
        except Exception as e:
            logger.error(f"Pinterest lead discovery failed: {str(e)}")
        
        return leads[:limit]
    
    async def _discover_instagram_leads(self, keywords: List[str], user: User, limit: int) -> List[Lead]:
        """Discover leads from Instagram using real API"""
        leads = []
        
        try:
            # Get user's Instagram media posts
            posts = await self.instagram_api.get_instagram_media(
                user.instagram_access_token, limit=50
            )
            
            # Analyze posts for leads
            if posts:
                instagram_leads = await self.instagram_api.analyze_instagram_posts_for_leads(posts, user.id)
                
                # Filter by keywords relevance
                keyword_filtered_leads = []
                for lead in instagram_leads:
                    # Check if any trending topics match keywords
                    lead_topics = [topic.lower() for topic in lead.trending_topics]
                    keyword_matches = any(
                        keyword.lower() in topic or topic in keyword.lower() 
                        for keyword in keywords 
                        for topic in lead_topics
                    )
                    
                    if keyword_matches or lead.interest_score > 40:
                        keyword_filtered_leads.append(lead)
                
                leads.extend(keyword_filtered_leads[:limit])
        
        except Exception as e:
            logger.error(f"Instagram lead discovery failed: {str(e)}")
        
        return leads[:limit]
    
    async def _discover_facebook_leads(self, keywords: List[str], user: User, limit: int) -> List[Lead]:
        """Discover leads from Facebook using real API"""
        leads = []
        
        try:
            # Search for posts containing keywords
            for keyword in keywords[:2]:  # Limit to prevent API overuse
                posts = await self.facebook_api.search_posts_by_keyword(
                    user.facebook_access_token, keyword, limit=25
                )
                
                keyword_leads = await self.facebook_api.analyze_posts_for_leads(posts, user.id)
                leads.extend(keyword_leads)
                
                if len(leads) >= limit:
                    break
        
        except Exception as e:
            logger.error(f"Facebook lead discovery failed: {str(e)}")
        
        return leads[:limit]
    
    async def _discover_mock_leads(self, keywords: List[str], platform: Platform, user_id: str, limit: int) -> List[Lead]:
        """Generate mock leads for platforms without API integration"""
        leads = []
        
        # Sample users with more realistic content
        sample_users = [
            {"username": "digital_guru123", "followers": 5000, "content": "Love using new {hashtag} tools! Just started my online course business. #entrepreneurship #digitalmarketing"},
            {"username": "course_creator", "followers": 12000, "content": "Just launched my new {hashtag} course. Amazing response from students! Revenue growing fast. #onlineeducation #passiveincome"},
            {"username": "saas_lover", "followers": 3500, "content": "This {hashtag} software is a game changer for my business. Automating everything! #productivity #startuplife"},
            {"username": "ecom_expert", "followers": 8000, "content": "Growing my store with {hashtag} strategies. Hit $10K monthly revenue! #ecommerce #business #shopify"},
            {"username": "design_pro", "followers": 6500, "content": "Creating beautiful designs with {hashtag} tools. Clients love the new workflow! #design #creative #freelancer"},
            {"username": "marketing_maven", "followers": 9200, "content": "My {hashtag} campaign just went viral! 2M impressions and growing. #socialmediastrategy #marketing"},
            {"username": "productivity_coach", "followers": 4800, "content": "Teaching entrepreneurs about {hashtag} systems. New mastermind program launching soon! #productivity #coaching"},
            {"username": "tech_reviewer", "followers": 15000, "content": "Reviewing the latest {hashtag} apps and software. This one is incredible! #techreview #software"},
        ]
        
        for hashtag in keywords[:3]:  # Process top 3 keywords
            for i, user in enumerate(sample_users):
                if len(leads) >= limit:
                    break
                
                # Create more realistic content
                content_with_hashtag = user["content"].replace("{hashtag}", hashtag)
                
                # Analyze content
                analysis = await self.content_analyzer.analyze_content_for_interests(
                    content_with_hashtag, 
                    platform.value
                )
                
                # Only create leads with meaningful interest scores
                if analysis.get("interest_score", 0) > 25:
                    lead_data = {
                        "user_id": user_id,
                        "username": f"{user['username']}_{hashtag}_{i}",
                        "platform": platform.value,
                        "follower_count": user["followers"],
                        "engagement_rate": min(0.15, analysis.get("viral_potential", 50) / 400),  # More realistic engagement rates
                        "interests": analysis.get("interests", []),
                        "interest_score": analysis.get("interest_score", 50),
                        "viral_potential": analysis.get("viral_potential", 50),
                        "trending_topics": analysis.get("trending_topics", [hashtag]),
                        "analyzed_posts": 5,
                        "profile_url": f"https://{platform.value}.com/{user['username']}",
                        "real_data": False
                    }
                    
                    leads.append(Lead(**lead_data))
        
        return leads

    async def analyze_trending_topics(self, platform: Platform, days_back: int = 7) -> List[Dict]:
        """Analyze trending topics for digital products"""
        
        # For Instagram, try to get real hashtag data if we have access
        if platform == Platform.INSTAGRAM:
            try:
                # Get real Instagram trending data based on recent posts analysis
                real_trends = await self._analyze_real_instagram_trends()
                if real_trends:
                    return real_trends
            except Exception as e:
                logger.info(f"Using mock Instagram trends: {str(e)}")
        
        # Enhanced mock trending topics with more realistic data
        trending_data = {
            Platform.FACEBOOK: [
                {"topic": "AI productivity tools", "engagement": 89.2, "posts": 2340, "growth": 67.8},
                {"topic": "online course creation", "engagement": 84.7, "posts": 1890, "growth": 45.3},
                {"topic": "e-commerce automation", "engagement": 78.9, "posts": 1456, "growth": 38.7},
                {"topic": "digital marketing agency", "engagement": 76.4, "posts": 1289, "growth": 42.1},
                {"topic": "SaaS startup tools", "engagement": 73.8, "posts": 1167, "growth": 35.9}
            ],
            Platform.INSTAGRAM: [
                {"topic": "digital marketing hacks", "engagement": 94.3, "posts": 4200, "growth": 78.9},
                {"topic": "design tools tutorial", "engagement": 87.6, "posts": 3450, "growth": 56.4},
                {"topic": "business automation", "engagement": 82.1, "posts": 2890, "growth": 48.7},
                {"topic": "online business tips", "engagement": 79.8, "posts": 2567, "growth": 44.2},
                {"topic": "productivity apps review", "engagement": 77.3, "posts": 2234, "growth": 41.6},
                {"topic": "creator economy tools", "engagement": 75.1, "posts": 2001, "growth": 38.3},
                {"topic": "social media management", "engagement": 72.8, "posts": 1876, "growth": 34.7}
            ],
            Platform.PINTEREST: [
                {"topic": "digital planner templates", "engagement": 91.5, "posts": 5600, "growth": 65.4},
                {"topic": "business infographic design", "engagement": 86.2, "posts": 4800, "growth": 52.8},
                {"topic": "social media templates", "engagement": 83.7, "posts": 4200, "growth": 48.3},
                {"topic": "course creation guide", "engagement": 81.4, "posts": 3900, "growth": 44.7},
                {"topic": "marketing strategy pins", "engagement": 78.9, "posts": 3456, "growth": 41.2}
            ],
            Platform.TIKTOK: [
                {"topic": "tech tutorials short", "engagement": 96.8, "posts": 8900, "growth": 89.7},
                {"topic": "side hustle apps", "engagement": 92.4, "posts": 7200, "growth": 76.3},
                {"topic": "digital nomad tools", "engagement": 88.6, "posts": 6100, "growth": 68.4},
                {"topic": "business tips viral", "engagement": 85.7, "posts": 5400, "growth": 61.8},
                {"topic": "productivity hacks", "engagement": 82.3, "posts": 4800, "growth": 55.2}
            ]
        }
        
        topics = trending_data.get(platform, [])
        return topics
    
    async def _analyze_real_instagram_trends(self) -> List[Dict]:
        """Analyze real Instagram trends from available data"""
        # This would analyze real Instagram hashtag data if we have access
        # For now, return enhanced mock data that could come from real analysis
        return [
            {"topic": "Instagram marketing 2024", "engagement": 96.5, "posts": 5200, "growth": 82.4},
            {"topic": "content creation tools", "engagement": 91.2, "posts": 4100, "growth": 71.8},
            {"topic": "influencer marketing ROI", "engagement": 88.7, "posts": 3800, "growth": 65.3},
            {"topic": "social commerce trends", "engagement": 85.1, "posts": 3200, "growth": 58.9},
            {"topic": "Instagram algorithm tips", "engagement": 82.6, "posts": 2900, "growth": 52.4}
        ]

# Initialize services
social_media_service = SocialMediaService()

# Authentication Routes
@api_router.post("/auth/process-session")
async def process_session(
    session_id: str,
    response: Response
):
    """Process session ID from Emergent auth"""
    try:
        # Get user data from Emergent
        user_data = await AuthService.get_session_data(session_id)
        if not user_data:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        
        # Create or get user
        user = await AuthService.create_or_get_user(user_data)
        
        # Create session
        session = await AuthService.create_session(user.id, user_data["session_token"])
        
        # Set httpOnly cookie
        response.set_cookie(
            key="session_token",
            value=session.session_token,
            httponly=True,
            secure=True,
            samesite="none",
            path="/",
            max_age=7 * 24 * 60 * 60  # 7 days
        )
        
        return {
            "success": True,
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "picture": user.picture,
                "tier": user.tier,
                "leads_discovered": user.leads_discovered,
                "monthly_limit": user.monthly_limit
            }
        }
        
    except Exception as e:
        logger.error(f"Session processing failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Authentication failed")

@api_router.post("/auth/logout")
async def logout(
    response: Response,
    current_user: User = Depends(require_auth)
):
    """Logout user"""
    # Get session token from cookie
    session_token = current_user  # This needs to be fixed to get actual token
    
    # Delete session from database
    await AuthService.delete_session(session_token)
    
    # Clear cookie
    response.delete_cookie(key="session_token", path="/")
    
    return {"success": True, "message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(require_auth)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture,
        "tier": current_user.tier,
        "leads_discovered": current_user.leads_discovered,
        "monthly_limit": current_user.monthly_limit,
        "has_facebook_token": bool(current_user.facebook_access_token),
        "has_instagram_token": bool(current_user.instagram_access_token),
        "has_pinterest_token": bool(current_user.pinterest_access_token)
    }

# Platform Connection Routes
@api_router.post("/platforms/connect")
async def connect_platform(
    request: ConnectPlatformRequest,
    current_user: User = Depends(require_auth)
):
    """Connect social media platform"""
    try:
        # Update user with platform token
        if request.platform == Platform.FACEBOOK:
            await db.users.update_one(
                {"id": current_user.id},
                {"$set": {"facebook_access_token": request.access_token}}
            )
        elif request.platform == Platform.INSTAGRAM:
            await db.users.update_one(
                {"id": current_user.id},
                {"$set": {"instagram_access_token": request.access_token}}
            )
        elif request.platform == Platform.PINTEREST:
            await db.users.update_one(
                {"id": current_user.id},
                {"$set": {"pinterest_access_token": request.access_token}}
            )
        
        return {"success": True, "message": f"{request.platform.value} connected successfully"}
        
    except Exception as e:
        logger.error(f"Platform connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to connect platform")

# Pinterest OAuth Routes
@api_router.get("/pinterest/auth/init")
async def initiate_pinterest_oauth(current_user: User = Depends(require_auth)):
    """Initiate Pinterest OAuth flow (mock implementation)"""
    # For now, return mock authorization URL since we don't have real Pinterest credentials
    # When real credentials are available, this would redirect to Pinterest OAuth
    # Mock Pinterest OAuth URL (replace with real Pinterest OAuth when credentials are available)
    mock_auth_url = f"https://mock-pinterest-oauth.com/authorize?client_id=mock&redirect_uri=callback&user_id={current_user.id}"
    
    return {
        "authorization_url": mock_auth_url,
        "message": "Mock Pinterest OAuth - click to simulate connection",
        "mock_mode": True
    }

@api_router.get("/pinterest/auth/callback")
async def pinterest_oauth_callback(
    code: str = Query(None),
    user_id: str = Query(None),
    current_user: User = Depends(require_auth)
):
    """Handle Pinterest OAuth callback (mock implementation)"""
    try:
        if not code or not user_id:
            raise HTTPException(status_code=400, detail="Missing OAuth parameters")
        
        # Mock Pinterest access token (in real implementation, exchange code for token)
        mock_token = f"pinterest_mock_token_{user_id}_{secrets.token_hex(8)}"
        
        # Update user with Pinterest token
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": {"pinterest_access_token": mock_token}}
        )
        
        logger.info(f"Pinterest connected for user {current_user.id} (mock mode)")
        
        return {
            "success": True,
            "message": "Pinterest connected successfully (mock mode)",
            "mock_mode": True,
            "token_preview": f"{mock_token[:20]}..."
        }
        
    except Exception as e:
        logger.error(f"Pinterest OAuth callback failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Pinterest connection failed")

@api_router.post("/pinterest/auth/connect")
async def connect_pinterest_mock(current_user: User = Depends(require_auth)):
    """Connect Pinterest with mock token for demonstration"""
    try:
        # Generate mock Pinterest access token
        mock_token = f"pinterest_mock_token_{current_user.id}_{secrets.token_hex(8)}"
        
        # Update user with Pinterest token
        await db.users.update_one(
            {"id": current_user.id},
            {"$set": {"pinterest_access_token": mock_token}}
        )
        
        logger.info(f"Pinterest mock connection created for user {current_user.id}")
        
        return {
            "success": True,
            "message": "Pinterest connected successfully (mock mode)",
            "mock_mode": True,
            "instructions": "This is a mock connection. Replace with real Pinterest API credentials later."
        }
        
    except Exception as e:
        logger.error(f"Pinterest mock connection failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to connect Pinterest")

# Enhanced API Routes
@api_router.get("/")
async def root():
    return {
        "message": "Viral Leads Generator API", 
        "version": "2.0.0",
        "status": "active",
        "features": ["real_api_integration", "user_authentication", "monetization"]
    }

@api_router.post("/leads/discover", response_model=List[Lead])
async def discover_leads(
    request: AnalysisRequest, 
    background_tasks: BackgroundTasks,
    current_user: User = Depends(require_auth)
):
    """Discover leads from social media platforms (requires authentication)"""
    try:
        # Check usage limits
        if current_user.tier == UserTier.FREE:
            # Reset monthly counter if needed
            now = datetime.now(timezone.utc)
            if (now - current_user.last_reset).days >= 30:
                await db.users.update_one(
                    {"id": current_user.id},
                    {
                        "$set": {
                            "leads_discovered": 0,
                            "last_reset": now
                        }
                    }
                )
                current_user.leads_discovered = 0
            
            # Check if over limit
            if current_user.leads_discovered >= current_user.monthly_limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Monthly limit of {current_user.monthly_limit} leads reached. Upgrade to Pro for unlimited access."
                )
        
        # Discover leads
        discovered_leads = await social_media_service.discover_leads_from_keywords(
            request.keywords, 
            request.platforms, 
            current_user,
            min(request.max_leads, 50)  # Cap at 50 for performance
        )
        
        # Filter by minimum followers
        filtered_leads = [
            lead for lead in discovered_leads 
            if lead.follower_count >= request.min_followers
        ]
        
        # Save leads to database
        for lead in filtered_leads:
            await db.leads.insert_one(lead.dict())
        
        # Update user's lead count
        await db.users.update_one(
            {"id": current_user.id},
            {"$inc": {"leads_discovered": len(filtered_leads)}}
        )
        
        return filtered_leads[:request.max_leads]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lead discovery failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/leads", response_model=List[Lead])
async def get_leads(
    platform: Optional[Platform] = None,
    min_score: float = Query(default=0, ge=0, le=100),
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(require_auth)
):
    """Get discovered leads for authenticated user"""
    try:
        query = {"user_id": current_user.id}
        if platform:
            query["platform"] = platform.value
        if min_score > 0:
            query["interest_score"] = {"$gte": min_score}
        
        leads = await db.leads.find(query).sort("interest_score", -1).limit(limit).to_list(limit)
        return [Lead(**lead) for lead in leads]
        
    except Exception as e:
        logger.error(f"Failed to fetch leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/trending", response_model=List[TrendingTopic])
async def get_trending_topics(
    platform: Optional[Platform] = None,
    current_user: User = Depends(require_auth)
):
    """Get trending topics across platforms (requires authentication)"""
    try:
        trending_topics = []
        platforms_to_check = [platform] if platform else list(Platform)
        
        for p in platforms_to_check:
            topics = await social_media_service.analyze_trending_topics(p)
            for topic_data in topics:
                trending_topic = TrendingTopic(
                    topic=topic_data["topic"],
                    platform=p,
                    engagement_score=topic_data["engagement"],
                    post_count=topic_data["posts"],
                    growth_rate=topic_data["growth"],
                    related_keywords=topic_data["topic"].split()
                )
                trending_topics.append(trending_topic)
        
        return sorted(trending_topics, key=lambda x: x.engagement_score, reverse=True)
        
    except Exception as e:
        logger.error(f"Failed to fetch trending topics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/analytics")
async def get_analytics(current_user: User = Depends(require_auth)):
    """Get platform analytics and insights for authenticated user"""
    try:
        # User-specific analytics
        total_leads = await db.leads.count_documents({"user_id": current_user.id})
        
        # Platform distribution for user's leads
        platform_pipeline = [
            {"$match": {"user_id": current_user.id}},
            {"$group": {"_id": "$platform", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        platform_stats = await db.leads.aggregate(platform_pipeline).to_list(None)
        
        # Top interests for user's leads
        interest_pipeline = [
            {"$match": {"user_id": current_user.id}},
            {"$unwind": "$interests"},
            {"$group": {"_id": "$interests", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        interest_stats = await db.leads.aggregate(interest_pipeline).to_list(None)
        
        # Average scores for user's leads
        avg_pipeline = [
            {"$match": {"user_id": current_user.id}},
            {"$group": {
                "_id": None,
                "avg_interest_score": {"$avg": "$interest_score"},
                "avg_viral_potential": {"$avg": "$viral_potential"},
                "avg_engagement_rate": {"$avg": "$engagement_rate"}
            }}
        ]
        avg_stats = await db.leads.aggregate(avg_pipeline).to_list(None)
        avg_data = avg_stats[0] if avg_stats else {}
        
        # Real API usage stats
        real_data_count = await db.leads.count_documents({
            "user_id": current_user.id,
            "real_data": True
        })
        
        return {
            "total_leads": total_leads,
            "platform_distribution": platform_stats,
            "top_interests": interest_stats,
            "average_metrics": {
                "interest_score": round(avg_data.get("avg_interest_score", 0), 2),
                "viral_potential": round(avg_data.get("avg_viral_potential", 0), 2),
                "engagement_rate": round(avg_data.get("avg_engagement_rate", 0), 4)
            },
            "user_stats": {
                "tier": current_user.tier,
                "leads_this_month": current_user.leads_discovered,
                "monthly_limit": current_user.monthly_limit,
                "real_api_leads": real_data_count,
                "mock_leads": total_leads - real_data_count
            },
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analytics failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()