from fastapi import FastAPI, APIRouter, HTTPException, BackgroundTasks, Query
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
from datetime import datetime, timedelta
from enum import Enum
import httpx
import json

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

class Lead(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
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
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    analyzed_posts: int = 0

class LeadCreate(BaseModel):
    username: str
    platform: Platform
    profile_url: Optional[str] = None

class AnalysisRequest(BaseModel):
    platforms: List[Platform]
    keywords: List[str]
    max_leads: int = Field(default=100, le=500)
    min_followers: int = Field(default=1000, ge=0)
    days_back: int = Field(default=30, le=90)

class TrendingTopic(BaseModel):
    topic: str
    platform: Platform
    engagement_score: float
    post_count: int
    growth_rate: float
    related_keywords: List[str]
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

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
2. Interest score (0-100)
3. Viral potential (0-100) based on engagement potential
4. Key topics/keywords mentioned
5. Purchase intent indicators

Return a JSON response with: interests, interest_score, viral_potential, trending_topics, purchase_intent"""
            ).with_model("openai", "gpt-4o-mini")
            
            user_message = UserMessage(
                text=f"Platform: {platform}\n\nContent to analyze:\n{content}\n\nAnalyze this content for digital product interests and return JSON with the specified fields."
            )
            
            response = await chat.send_message(user_message)
            
            # Parse the JSON response
            try:
                analysis = json.loads(response.strip())
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
            "digital_marketing": ["seo", "marketing", "ads", "social media", "content", "brand"],
            "online_courses": ["course", "learn", "training", "education", "skill", "tutorial"],
            "saas_tools": ["software", "app", "tool", "platform", "automation", "crm"],
            "ecommerce": ["shop", "store", "sell", "product", "business", "revenue"],
            "design_tools": ["design", "creative", "ui", "ux", "graphics", "visual"],
            "productivity": ["productivity", "efficient", "organize", "manage", "workflow"],
            "business_tools": ["business", "entrepreneur", "startup", "growth", "strategy"]
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
        digital_keywords = ["digital", "online", "software", "course", "tool", "app", "platform"]
        score += sum(5 for keyword in digital_keywords if keyword in content_lower)
        
        # Engagement indicators
        engagement_words = ["love", "recommend", "amazing", "game changer", "must have"]
        score += sum(10 for word in engagement_words if word in content_lower)
        
        # Intent indicators
        intent_words = ["looking for", "need", "searching", "want", "buying"]
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
            if len(word) > 3 and word not in ["this", "that", "with", "from", "they", "have"]:
                relevant_words.append(word)
        
        return (hashtags + relevant_words)[:5]

class SocialMediaService:
    def __init__(self):
        self.content_analyzer = ContentAnalysisService()
    
    async def discover_leads_from_hashtags(self, hashtags: List[str], platform: Platform, limit: int = 50) -> List[Dict]:
        """Mock implementation - in real app, this would use actual social media APIs"""
        leads = []
        
        # Simulate discovering leads based on hashtags
        sample_users = [
            {"username": "digital_guru123", "followers": 5000, "content": f"Love using new {hashtag} tools! #entrepreneurship #digitalmarketing"},
            {"username": "course_creator", "followers": 12000, "content": f"Just launched my new {hashtag} course. Amazing response! #onlineeducation"},
            {"username": "saas_lover", "followers": 3500, "content": f"This {hashtag} software is a game changer for my business #productivity"},
            {"username": "ecom_expert", "followers": 8000, "content": f"Growing my store with {hashtag} strategies #ecommerce #business"},
            {"username": "design_pro", "followers": 6500, "content": f"Creating beautiful designs with {hashtag} tools #design #creative"},
        ]
        
        for hashtag in hashtags[:3]:  # Process top 3 hashtags
            for i, user in enumerate(sample_users):
                if len(leads) >= limit:
                    break
                    
                # Analyze content
                content_with_hashtag = user["content"].replace("{hashtag}", hashtag)
                analysis = await self.content_analyzer.analyze_content_for_interests(
                    content_with_hashtag, 
                    platform.value
                )
                
                lead_data = {
                    "username": f"{user['username']}_{hashtag}_{i}",
                    "platform": platform.value,
                    "follower_count": user["followers"],
                    "engagement_rate": analysis.get("viral_potential", 50) / 100,
                    "interests": analysis.get("interests", []),
                    "interest_score": analysis.get("interest_score", 50),
                    "viral_potential": analysis.get("viral_potential", 50),
                    "trending_topics": analysis.get("trending_topics", [hashtag]),
                    "analyzed_posts": 5,
                    "profile_url": f"https://{platform.value}.com/{user['username']}"
                }
                
                leads.append(lead_data)
        
        return leads

    async def analyze_trending_topics(self, platform: Platform, days_back: int = 7) -> List[Dict]:
        """Analyze trending topics for digital products"""
        # Mock trending topics - in real app, this would analyze actual platform data
        trending_data = {
            Platform.FACEBOOK: [
                {"topic": "AI productivity tools", "engagement": 85.5, "posts": 1200, "growth": 45.2},
                {"topic": "online course creation", "engagement": 78.3, "posts": 890, "growth": 32.1},
                {"topic": "e-commerce automation", "engagement": 72.1, "posts": 756, "growth": 28.5}
            ],
            Platform.INSTAGRAM: [
                {"topic": "digital marketing hacks", "engagement": 92.1, "posts": 2100, "growth": 67.8},
                {"topic": "design tools", "engagement": 81.4, "posts": 1450, "growth": 41.2},
                {"topic": "business apps", "engagement": 75.6, "posts": 1120, "growth": 35.9}
            ],
            Platform.PINTEREST: [
                {"topic": "productivity planners", "engagement": 88.7, "posts": 3200, "growth": 52.3},
                {"topic": "digital templates", "engagement": 83.2, "posts": 2800, "growth": 48.1},
                {"topic": "online business ideas", "engagement": 79.5, "posts": 1900, "growth": 39.7}
            ],
            Platform.TIKTOK: [
                {"topic": "tech tutorials", "engagement": 94.3, "posts": 5600, "growth": 78.9},
                {"topic": "side hustle apps", "engagement": 87.6, "posts": 4200, "growth": 65.4},
                {"topic": "digital nomad tools", "engagement": 82.1, "posts": 3100, "growth": 44.8}
            ]
        }
        
        topics = trending_data.get(platform, [])
        return topics

# Initialize services
social_media_service = SocialMediaService()

# API Routes
@api_router.get("/")
async def root():
    return {
        "message": "Viral Leads Generator API", 
        "version": "1.0.0",
        "status": "active"
    }

@api_router.post("/leads/discover", response_model=List[Lead])
async def discover_leads(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """Discover leads from social media platforms based on keywords"""
    try:
        all_leads = []
        
        for platform in request.platforms:
            # Discover leads for this platform
            platform_leads = await social_media_service.discover_leads_from_hashtags(
                request.keywords, platform, request.max_leads // len(request.platforms)
            )
            
            # Convert to Lead objects and save to database
            for lead_data in platform_leads:
                if lead_data["follower_count"] >= request.min_followers:
                    lead = Lead(**lead_data)
                    all_leads.append(lead)
                    
                    # Save to database in background
                    background_tasks.add_task(save_lead_to_db, lead)
        
        return all_leads[:request.max_leads]
        
    except Exception as e:
        logger.error(f"Lead discovery failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/leads", response_model=List[Lead])
async def get_leads(
    platform: Optional[Platform] = None,
    min_score: float = Query(default=0, ge=0, le=100),
    limit: int = Query(default=50, le=200)
):
    """Get discovered leads with filtering options"""
    try:
        query = {}
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
async def get_trending_topics(platform: Optional[Platform] = None):
    """Get trending topics across platforms"""
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
async def get_analytics():
    """Get platform analytics and insights"""
    try:
        total_leads = await db.leads.count_documents({})
        
        # Platform distribution
        platform_pipeline = [
            {"$group": {"_id": "$platform", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        platform_stats = await db.leads.aggregate(platform_pipeline).to_list(None)
        
        # Top interests
        interest_pipeline = [
            {"$unwind": "$interests"},
            {"$group": {"_id": "$interests", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        interest_stats = await db.leads.aggregate(interest_pipeline).to_list(None)
        
        # Average scores
        avg_pipeline = [
            {"$group": {
                "_id": None,
                "avg_interest_score": {"$avg": "$interest_score"},
                "avg_viral_potential": {"$avg": "$viral_potential"},
                "avg_engagement_rate": {"$avg": "$engagement_rate"}
            }}
        ]
        avg_stats = await db.leads.aggregate(avg_pipeline).to_list(None)
        avg_data = avg_stats[0] if avg_stats else {}
        
        return {
            "total_leads": total_leads,
            "platform_distribution": platform_stats,
            "top_interests": interest_stats,
            "average_metrics": {
                "interest_score": round(avg_data.get("avg_interest_score", 0), 2),
                "viral_potential": round(avg_data.get("avg_viral_potential", 0), 2),
                "engagement_rate": round(avg_data.get("avg_engagement_rate", 0), 4)
            },
            "last_updated": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Analytics failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def save_lead_to_db(lead: Lead):
    """Save lead to database"""
    try:
        await db.leads.insert_one(lead.dict())
    except Exception as e:
        logger.error(f"Failed to save lead: {str(e)}")

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