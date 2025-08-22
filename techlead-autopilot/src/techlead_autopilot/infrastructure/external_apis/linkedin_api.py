"""
LinkedIn API Client with OAuth 2.0 authentication and posting capabilities.

Integrates with LinkedIn API for automated content posting and engagement tracking.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, List
from urllib.parse import urlencode
import json

import aiohttp
from cryptography.fernet import Fernet

from ...config import get_settings

logger = logging.getLogger(__name__)


class LinkedInOAuthError(Exception):
    """LinkedIn OAuth authentication error."""
    pass


class LinkedInPostingError(Exception):
    """LinkedIn content posting error.""" 
    pass


class LinkedInAPIClient:
    """
    LinkedIn API client for OAuth authentication and content posting.
    
    Features:
    - OAuth 2.0 authentication flow
    - Content posting with optimal formatting
    - Engagement metrics tracking
    - Rate limiting and error handling
    - Token encryption and refresh
    """
    
    # LinkedIn API endpoints
    BASE_URL = "https://api.linkedin.com"
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    
    # Required scopes for content posting and profile access
    REQUIRED_SCOPES = [
        "r_liteprofile",      # Basic profile information
        "r_emailaddress",     # Email address
        "w_member_social",    # Post content
        "r_organization_social",  # Read organization posts (for analytics)
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self.client_id = self.settings.linkedin_client_id
        self.client_secret = self.settings.linkedin_client_secret
        self.redirect_uri = self.settings.linkedin_redirect_uri
        
        # Initialize encryption for token storage
        self.encryption_key = self._get_encryption_key()
        self.fernet = Fernet(self.encryption_key)
        
        # Rate limiting: LinkedIn allows 100 requests per day for posting
        self.rate_limit = {
            "posts_per_day": 2,  # Conservative limit for quality content
            "requests_per_hour": 30,
            "last_reset": datetime.utcnow(),
            "requests_today": 0,
            "posts_today": 0
        }
        
    def get_authorization_url(self, state: str = None) -> str:
        """
        Generate LinkedIn OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL for user to visit
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": " ".join(self.REQUIRED_SCOPES)
        }
        
        if state:
            params["state"] = state
            
        auth_url = f"{self.AUTH_URL}?{urlencode(params)}"
        logger.info(f"Generated LinkedIn auth URL: {auth_url}")
        return auth_url
    
    async def exchange_code_for_tokens(self, authorization_code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access and refresh tokens.
        
        Args:
            authorization_code: Code received from OAuth callback
            
        Returns:
            Dictionary containing access_token, expires_in, and user info
            
        Raises:
            LinkedInOAuthError: If token exchange fails
        """
        logger.info("Exchanging authorization code for LinkedIn tokens")
        
        token_data = {
            "grant_type": "authorization_code",
            "code": authorization_code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                # Exchange code for tokens
                async with session.post(
                    self.TOKEN_URL,
                    data=token_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"LinkedIn token exchange failed: {error_text}")
                        raise LinkedInOAuthError(f"Token exchange failed: {error_text}")
                    
                    token_response = await response.json()
                    access_token = token_response["access_token"]
                    expires_in = token_response.get("expires_in", 5183940)  # ~60 days
                    
                # Get user profile information
                user_info = await self._get_user_profile(session, access_token)
                
                # Calculate expiration timestamp
                expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                
                result = {
                    "access_token": access_token,
                    "expires_in": expires_in,
                    "expires_at": expires_at.isoformat(),
                    "user_info": user_info,
                    "scopes": self.REQUIRED_SCOPES
                }
                
                logger.info(f"Successfully obtained LinkedIn tokens for user {user_info.get('id')}")
                return result
                
            except aiohttp.ClientError as e:
                logger.error(f"HTTP error during LinkedIn token exchange: {e}")
                raise LinkedInOAuthError(f"Network error: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from LinkedIn: {e}")
                raise LinkedInOAuthError(f"Invalid response format: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during LinkedIn token exchange: {e}")
                raise LinkedInOAuthError(f"Unexpected error: {e}")
    
    async def _get_user_profile(self, session: aiohttp.ClientSession, access_token: str) -> Dict[str, Any]:
        """Get user profile information from LinkedIn API."""
        headers = {"Authorization": f"Bearer {access_token}"}
        
        # Get basic profile info
        async with session.get(
            f"{self.BASE_URL}/v2/people/~",
            headers=headers
        ) as response:
            if response.status != 200:
                logger.warning(f"Failed to get LinkedIn profile: {response.status}")
                return {}
            
            profile_data = await response.json()
        
        # Get email address
        try:
            async with session.get(
                f"{self.BASE_URL}/v2/emailAddress?q=members&projection=(elements*(handle~))",
                headers=headers
            ) as response:
                if response.status == 200:
                    email_data = await response.json()
                    if "elements" in email_data and len(email_data["elements"]) > 0:
                        profile_data["email"] = email_data["elements"][0]["handle~"]["emailAddress"]
        except Exception as e:
            logger.warning(f"Failed to get LinkedIn email: {e}")
        
        return {
            "id": profile_data.get("id"),
            "first_name": profile_data.get("localizedFirstName"),
            "last_name": profile_data.get("localizedLastName"),
            "profile_picture": profile_data.get("profilePicture", {}).get("displayImage~", {}).get("elements", [{}])[-1].get("identifiers", [{}])[-1].get("identifier"),
            "email": profile_data.get("email"),
            "headline": profile_data.get("headline", {}).get("localized", {})
        }
    
    async def post_content(
        self,
        access_token: str,
        user_urn: str,
        content: str,
        visibility: str = "PUBLIC"
    ) -> Dict[str, Any]:
        """
        Post content to LinkedIn.
        
        Args:
            access_token: Valid LinkedIn access token
            user_urn: LinkedIn user URN (format: urn:li:person:PERSON_ID)
            content: Content text to post
            visibility: Post visibility (PUBLIC, CONNECTIONS)
            
        Returns:
            Dictionary with post details and LinkedIn post ID
            
        Raises:
            LinkedInPostingError: If posting fails
        """
        # Check rate limits
        if not self._check_rate_limit():
            raise LinkedInPostingError("Daily posting limit exceeded")
        
        logger.info(f"Posting content to LinkedIn for user {user_urn}")
        
        # Prepare post data according to LinkedIn UGC API v2
        post_data = {
            "author": user_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": visibility
            }
        }
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.BASE_URL}/v2/ugcPosts",
                    json=post_data,
                    headers=headers
                ) as response:
                    
                    response_text = await response.text()
                    
                    if response.status == 201:
                        # Extract post ID from response
                        response_data = json.loads(response_text) if response_text else {}
                        post_id = response_data.get("id", "")
                        
                        # Update rate limiting
                        self._update_rate_limit()
                        
                        logger.info(f"Successfully posted to LinkedIn: {post_id}")
                        return {
                            "success": True,
                            "post_id": post_id,
                            "status": "published",
                            "posted_at": datetime.utcnow().isoformat(),
                            "content_length": len(content)
                        }
                    else:
                        logger.error(f"LinkedIn posting failed: {response.status} - {response_text}")
                        raise LinkedInPostingError(f"Posting failed: {response.status} - {response_text}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Network error during LinkedIn posting: {e}")
                raise LinkedInPostingError(f"Network error: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON response from LinkedIn posting: {e}")
                raise LinkedInPostingError(f"Invalid response format: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during LinkedIn posting: {e}")
                raise LinkedInPostingError(f"Unexpected error: {e}")
    
    async def get_post_analytics(
        self,
        access_token: str,
        post_urn: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get analytics data for a LinkedIn post.
        
        Args:
            access_token: Valid LinkedIn access token
            post_urn: LinkedIn post URN
            
        Returns:
            Analytics data including likes, comments, shares, impressions
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                # Get post engagement metrics
                analytics_url = f"{self.BASE_URL}/v2/socialMetadata/{post_urn}"
                
                async with session.get(analytics_url, headers=headers) as response:
                    if response.status != 200:
                        logger.warning(f"Failed to get LinkedIn post analytics: {response.status}")
                        return None
                    
                    analytics_data = await response.json()
                    
                    return {
                        "likes": analytics_data.get("numLikes", 0),
                        "comments": analytics_data.get("numComments", 0), 
                        "shares": analytics_data.get("numShares", 0),
                        "impressions": analytics_data.get("numViews", 0),
                        "engagement_rate": self._calculate_engagement_rate(analytics_data),
                        "retrieved_at": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Error retrieving LinkedIn post analytics: {e}")
            return None
    
    def encrypt_token(self, token: str) -> str:
        """Encrypt access token for secure storage."""
        return self.fernet.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt access token from storage."""
        return self.fernet.decrypt(encrypted_token.encode()).decode()
    
    def _get_encryption_key(self) -> bytes:
        """Generate or retrieve encryption key for token storage."""
        # In production, this should be stored securely (e.g., environment variable)
        # For now, derive from JWT secret
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        import base64
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"linkedin_token_salt",  # Should be unique per installation
            iterations=100000
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.settings.jwt_secret_key.encode()))
        return key
    
    def _check_rate_limit(self) -> bool:
        """Check if we can make another post within rate limits."""
        now = datetime.utcnow()
        
        # Reset daily counters if it's a new day
        if now.date() > self.rate_limit["last_reset"].date():
            self.rate_limit["posts_today"] = 0
            self.rate_limit["requests_today"] = 0
            self.rate_limit["last_reset"] = now
        
        # Check daily posting limit
        if self.rate_limit["posts_today"] >= self.rate_limit["posts_per_day"]:
            logger.warning(f"LinkedIn daily posting limit reached: {self.rate_limit['posts_today']}")
            return False
        
        return True
    
    def _update_rate_limit(self):
        """Update rate limiting counters after successful post."""
        self.rate_limit["posts_today"] += 1
        self.rate_limit["requests_today"] += 1
        logger.info(f"LinkedIn posts today: {self.rate_limit['posts_today']}/{self.rate_limit['posts_per_day']}")
    
    def _calculate_engagement_rate(self, analytics_data: Dict[str, Any]) -> float:
        """Calculate engagement rate from LinkedIn analytics data."""
        likes = analytics_data.get("numLikes", 0)
        comments = analytics_data.get("numComments", 0)
        shares = analytics_data.get("numShares", 0)
        impressions = analytics_data.get("numViews", 0)
        
        if impressions == 0:
            return 0.0
        
        total_engagement = likes + comments + shares
        return total_engagement / impressions
    
    async def validate_token(self, access_token: str) -> bool:
        """
        Validate if an access token is still valid.
        
        Args:
            access_token: LinkedIn access token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/v2/people/~",
                    headers=headers
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"Error validating LinkedIn token: {e}")
            return False
    
    def format_content_for_linkedin(self, content: str) -> str:
        """
        Format content for optimal LinkedIn posting.
        
        Args:
            content: Raw content to format
            
        Returns:
            LinkedIn-optimized content
        """
        # LinkedIn best practices:
        # - Keep posts under 1300 characters for full visibility
        # - Use line breaks for readability
        # - Include hashtags at the end
        
        if len(content) > 1300:
            # Truncate while preserving hashtags
            lines = content.split('\n')
            hashtag_lines = [line for line in lines if line.strip().startswith('#')]
            content_lines = [line for line in lines if not line.strip().startswith('#')]
            
            # Truncate content to leave room for hashtags
            hashtag_length = sum(len(line) + 1 for line in hashtag_lines)
            max_content_length = 1300 - hashtag_length - 10  # Buffer
            
            truncated_content = content[:max_content_length].rsplit(' ', 1)[0] + "..."
            
            if hashtag_lines:
                content = truncated_content + '\n\n' + '\n'.join(hashtag_lines)
            else:
                content = truncated_content
        
        return content