"""
Integration tests for LinkedIn OAuth and posting functionality.

Tests the complete LinkedIn integration flow including:
- OAuth 2.0 authorization and token management
- Content posting to LinkedIn API
- Engagement metrics synchronization
- Error handling and retry mechanisms
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from techlead_autopilot.services.linkedin_service import LinkedInService
from techlead_autopilot.infrastructure.database.models import LinkedInIntegration, User, Organization


class TestLinkedInOAuthFlow:
    """Test LinkedIn OAuth 2.0 flow implementation."""
    
    @pytest.fixture
    def mock_user(self):
        """Mock user for testing."""
        user = Mock()
        user.id = uuid4()
        user.email = "test@example.com"
        user.organization_id = uuid4()
        return user
    
    @pytest.fixture
    def linkedin_service(self):
        """LinkedIn service instance for testing."""
        return LinkedInService()
    
    def test_oauth_authorization_url_generation(self, linkedin_service, mock_user):
        """
        Test that OAuth authorization URL is generated correctly with required scopes.
        
        The URL should include:
        - LinkedIn OAuth endpoint
        - Required scopes: w_member_social, r_liteprofile, r_emailaddress
        - State parameter for security
        - Redirect URI for callback handling
        """
        # This test should fail initially since LinkedInService doesn't exist yet
        redirect_uri = "https://app.techleadautopilot.com/auth/linkedin/callback"
        state = "secure_random_state_123"
        
        auth_url = linkedin_service.get_authorization_url(
            redirect_uri=redirect_uri,
            state=state,
            user_id=mock_user.id
        )
        
        # Verify LinkedIn OAuth endpoint
        assert "https://www.linkedin.com/oauth/v2/authorization" in auth_url
        
        # Verify required scopes are present (URL encoding can use + or %20 for spaces)
        assert ("scope=w_member_social+r_liteprofile+r_emailaddress" in auth_url or 
                "scope=w_member_social%20r_liteprofile%20r_emailaddress" in auth_url)
        
        # Verify security parameters
        assert f"state={state}" in auth_url
        # Check for URL-encoded redirect URI
        from urllib.parse import quote
        encoded_redirect_uri = quote(redirect_uri, safe='')
        assert f"redirect_uri={encoded_redirect_uri}" in auth_url
    
    @pytest.mark.asyncio
    async def test_oauth_token_exchange(self, linkedin_service, mock_user):
        """
        Test OAuth token exchange after user authorization.
        
        Should exchange authorization code for access and refresh tokens,
        then store them securely in the database.
        """
        authorization_code = "mock_auth_code_123"
        redirect_uri = "https://app.techleadautopilot.com/auth/linkedin/callback"
        
        # Mock LinkedIn token response
        mock_token_response = {
            "access_token": "mock_access_token_xyz",
            "expires_in": 5184000,  # 60 days in seconds
            "refresh_token": "mock_refresh_token_abc",
            "scope": "w_member_social,r_liteprofile,r_emailaddress"
        }
        
        # Mock LinkedIn profile response
        mock_profile_response = {
            "id": "linkedin_user_123",
            "firstName": {"localized": {"en_US": "John"}},
            "lastName": {"localized": {"en_US": "Doe"}},
            "profilePicture": {
                "displayImage": "urn:li:digitalmediaAsset:profile-photo-123"
            }
        }
        
        with patch.object(linkedin_service, '_exchange_code_for_tokens', 
                         return_value=mock_token_response) as mock_exchange:
            with patch.object(linkedin_service, '_get_user_profile',
                            return_value=mock_profile_response) as mock_profile:
                
                integration = await linkedin_service.handle_oauth_callback(
                    code=authorization_code,
                    redirect_uri=redirect_uri,
                    user_id=mock_user.id,
                    organization_id=mock_user.organization_id
                )
                
                # Verify token exchange was called
                mock_exchange.assert_called_once_with(authorization_code, redirect_uri)
                
                # Verify profile fetch was called
                mock_profile.assert_called_once_with(mock_token_response["access_token"])
                
                # Verify integration object is created correctly
                assert integration.linkedin_user_id == "linkedin_user_123"
                assert integration.access_token is not None  # Should be encrypted
                assert integration.refresh_token is not None  # Should be encrypted
                assert integration.is_active is True
                assert integration.user_id == mock_user.id
    
    @pytest.mark.asyncio
    async def test_token_refresh_mechanism(self, linkedin_service):
        """
        Test automatic token refresh when access token expires.
        
        Should detect expired tokens and refresh them using refresh token,
        then update the stored credentials.
        """
        # Mock existing integration with expired token
        mock_integration = Mock()
        mock_integration.access_token = "expired_token"
        mock_integration.refresh_token = "valid_refresh_token"
        mock_integration.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)  # Expired
        
        # Mock successful token refresh response
        mock_refresh_response = {
            "access_token": "new_access_token_xyz",
            "expires_in": 5184000,
            "refresh_token": "new_refresh_token_abc"
        }
        
        with patch.object(linkedin_service, '_refresh_access_token',
                         return_value=mock_refresh_response) as mock_refresh:
            
            refreshed_integration = await linkedin_service.refresh_token_if_needed(mock_integration)
            
            # Verify refresh was called with correct refresh token
            mock_refresh.assert_called_once_with("valid_refresh_token")
            
            # Verify integration was updated
            assert refreshed_integration.access_token == "new_access_token_xyz"
            assert refreshed_integration.refresh_token == "new_refresh_token_abc"
            assert refreshed_integration.token_expires_at > datetime.now(timezone.utc)
    
    @pytest.mark.asyncio
    async def test_oauth_error_handling(self, linkedin_service, mock_user):
        """
        Test error handling in OAuth flow.
        
        Should handle various error scenarios:
        - Invalid authorization code
        - Network failures
        - LinkedIn API errors
        - Token refresh failures
        """
        authorization_code = "invalid_code"
        redirect_uri = "https://app.techleadautopilot.com/auth/linkedin/callback"
        
        # Mock LinkedIn API error response
        with patch.object(linkedin_service, '_exchange_code_for_tokens',
                         side_effect=Exception("Invalid authorization code")):
            
            with pytest.raises(Exception) as exc_info:
                await linkedin_service.handle_oauth_callback(
                    code=authorization_code,
                    redirect_uri=redirect_uri,
                    user_id=mock_user.id,
                    organization_id=mock_user.organization_id
                )
            
            assert "Invalid authorization code" in str(exc_info.value)


class TestLinkedInPosting:
    """Test LinkedIn content posting functionality."""
    
    @pytest.fixture
    def mock_integration(self):
        """Mock LinkedIn integration with valid tokens."""
        integration = Mock()
        integration.access_token = "valid_access_token"
        integration.linkedin_user_id = "linkedin_user_123"
        integration.is_active = True
        integration.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        return integration
    
    @pytest.fixture
    def linkedin_service(self):
        """LinkedIn service instance for testing."""
        return LinkedInService()
    
    @pytest.mark.asyncio
    async def test_content_posting_success(self, linkedin_service, mock_integration):
        """
        Test successful content posting to LinkedIn.
        
        Should format content correctly and post via LinkedIn API,
        then return posting confirmation with post ID.
        """
        content_data = {
            "text": "Test LinkedIn post content with proven engagement patterns #TechLeadership",
            "content_type": "thought_leadership",
            "hashtags": ["#TechLeadership", "#EngineeringManagement"]
        }
        
        # Mock successful LinkedIn post response
        mock_post_response = {
            "id": "urn:li:activity:1234567890",
            "created": {"time": int(datetime.now(timezone.utc).timestamp() * 1000)}
        }
        
        with patch.object(linkedin_service, '_post_to_linkedin_api',
                         return_value=mock_post_response) as mock_post:
            
            post_result = await linkedin_service.post_content(
                integration=mock_integration,
                content=content_data
            )
            
            # Verify LinkedIn API was called with formatted content
            mock_post.assert_called_once()
            call_args = mock_post.call_args[1]
            assert call_args['access_token'] == mock_integration.access_token
            assert content_data["text"] in call_args['content']['text']
            
            # Verify post result contains LinkedIn post ID
            assert post_result.linkedin_post_id == "urn:li:activity:1234567890"
            assert post_result.posted_at is not None
            assert post_result.status == "posted"
    
    @pytest.mark.asyncio
    async def test_posting_with_expired_token_refresh(self, linkedin_service):
        """
        Test posting with expired token automatically refreshes and retries.
        
        Should detect expired token, refresh it, then retry posting.
        """
        # Mock integration with expired token
        mock_integration = Mock()
        mock_integration.access_token = "expired_token"
        mock_integration.refresh_token = "valid_refresh_token"
        mock_integration.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        content_data = {"text": "Test post content"}
        
        # Mock token refresh and successful post
        with patch.object(linkedin_service, 'refresh_token_if_needed',
                         return_value=mock_integration) as mock_refresh:
            with patch.object(linkedin_service, '_post_to_linkedin_api',
                            return_value={"id": "urn:li:activity:1234567890"}) as mock_post:
                
                await linkedin_service.post_content(
                    integration=mock_integration,
                    content=content_data
                )
                
                # Verify token was refreshed before posting
                mock_refresh.assert_called_once_with(mock_integration)
                mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_posting_rate_limit_handling(self, linkedin_service, mock_integration):
        """
        Test handling of LinkedIn API rate limits.
        
        Should implement exponential backoff and respect rate limit headers.
        """
        content_data = {"text": "Test post content"}
        
        # Mock rate limit error response
        rate_limit_error = Exception("Rate limit exceeded")
        rate_limit_error.status_code = 429
        rate_limit_error.headers = {"Retry-After": "60"}
        
        with patch.object(linkedin_service, '_post_to_linkedin_api',
                         side_effect=rate_limit_error) as mock_post:
            
            with pytest.raises(Exception) as exc_info:
                await linkedin_service.post_content(
                    integration=mock_integration,
                    content=content_data
                )
            
            assert "Rate limit exceeded" in str(exc_info.value)
            mock_post.assert_called_once()


class TestLinkedInAnalytics:
    """Test LinkedIn engagement analytics synchronization."""
    
    @pytest.fixture
    def linkedin_service(self):
        """LinkedIn service instance for testing."""
        return LinkedInService()
    
    @pytest.mark.asyncio
    async def test_engagement_metrics_sync(self, linkedin_service):
        """
        Test synchronization of engagement metrics from LinkedIn.
        
        Should fetch likes, comments, shares, and impressions data
        and update the content record with real engagement data.
        """
        mock_integration = Mock()
        mock_integration.access_token = "valid_token"
        
        linkedin_post_id = "urn:li:activity:1234567890"
        
        # Mock LinkedIn analytics response
        mock_analytics_response = {
            "likes": 45,
            "comments": 12,
            "shares": 8,
            "impressions": 1250,
            "clicks": 85
        }
        
        with patch.object(linkedin_service, '_get_post_analytics',
                         return_value=mock_analytics_response) as mock_analytics:
            
            engagement_data = await linkedin_service.sync_engagement_metrics(
                integration=mock_integration,
                linkedin_post_id=linkedin_post_id
            )
            
            # Verify analytics API was called
            mock_analytics.assert_called_once_with(
                access_token=mock_integration.access_token,
                post_id=linkedin_post_id
            )
            
            # Verify engagement data is returned correctly
            assert engagement_data.likes == 45
            assert engagement_data.comments == 12
            assert engagement_data.shares == 8
            assert engagement_data.impressions == 1250
            assert engagement_data.engagement_rate > 0  # Should calculate engagement rate
    
    @pytest.mark.asyncio
    async def test_bulk_analytics_sync(self, linkedin_service):
        """
        Test bulk synchronization of analytics for multiple posts.
        
        Should efficiently batch API calls and update multiple posts
        with their latest engagement metrics.
        """
        mock_integration = Mock()
        mock_integration.access_token = "valid_token"
        
        post_ids = [
            "urn:li:activity:1234567890",
            "urn:li:activity:1234567891",
            "urn:li:activity:1234567892"
        ]
        
        # Mock batch analytics response
        mock_batch_response = {
            "urn:li:activity:1234567890": {"likes": 45, "comments": 12},
            "urn:li:activity:1234567891": {"likes": 32, "comments": 8},
            "urn:li:activity:1234567892": {"likes": 67, "comments": 15}
        }
        
        with patch.object(linkedin_service, '_get_bulk_post_analytics',
                         return_value=mock_batch_response) as mock_batch:
            
            results = await linkedin_service.sync_bulk_engagement_metrics(
                integration=mock_integration,
                post_ids=post_ids
            )
            
            # Verify bulk API was called once (not per post)
            mock_batch.assert_called_once_with(
                access_token=mock_integration.access_token,
                post_ids=post_ids
            )
            
            # Verify all posts have updated metrics
            assert len(results) == 3
            assert all(result.likes > 0 for result in results)
            assert all(result.comments > 0 for result in results)