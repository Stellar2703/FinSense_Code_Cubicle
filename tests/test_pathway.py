import pytest
import os
import sys
import json
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.pathway_integration import integrate_pathway_with_realtime
from app.services.pathway_pipelines import is_available, run_pathway_pipelines


class TestPathwayIntegration:
    """Test Pathway integration functionality"""
    
    @patch('app.services.pathway_pipelines.PATHWAY_AVAILABLE', True)
    @patch('app.services.pathway_pipelines.pw')
    def test_pathway_availability(self, mock_pw):
        """Test if Pathway availability check works"""
        assert is_available() is True
    
    @patch('app.services.pathway_pipelines.PATHWAY_AVAILABLE', False)
    def test_pathway_not_available(self):
        """Test behavior when Pathway is not available"""
        assert is_available() is False
    
    @pytest.mark.asyncio
    @patch('app.services.pathway_pipelines.PATHWAY_AVAILABLE', True)
    @patch('app.services.pathway_pipelines.run_pathway_pipelines')
    async def test_pathway_integration(self, mock_run_pipelines):
        """Test Pathway integration with app state"""
        # Mock successful pipeline run
        mock_run_pipelines.return_value = True
        
        # Create mock state and alerts objects
        mock_state = MagicMock()
        mock_alerts = MagicMock()
        
        # Test successful integration
        result = await integrate_pathway_with_realtime(mock_state, mock_alerts)
        assert result is True
        mock_run_pipelines.assert_called_once_with(mock_state, mock_alerts)
    
    @pytest.mark.asyncio
    @patch('app.services.pathway_pipelines.PATHWAY_AVAILABLE', False)
    async def test_pathway_integration_fallback(self):
        """Test fallback when Pathway is not available"""
        # Create mock state and alerts objects
        mock_state = MagicMock()
        mock_alerts = MagicMock()
        
        # Test fallback behavior
        result = await integrate_pathway_with_realtime(mock_state, mock_alerts)
        assert result is False


class TestPathwayPipelines:
    """Test Pathway pipeline functionality"""
    
    @patch('app.services.pathway_pipelines.PATHWAY_AVAILABLE', True)
    @patch('app.services.pathway_pipelines.pw')
    def test_create_market_pipeline(self, mock_pw):
        """Test market data pipeline creation"""
        from app.services.pathway_pipelines import create_market_pipeline
        
        # Mock objects
        mock_state = MagicMock()
        mock_alerts = MagicMock()
        mock_table = MagicMock()
        mock_processed = MagicMock()
        
        # Configure mock behavior
        mock_pw.io.http.read.return_value = mock_table
        mock_table.select.return_value = mock_processed
        
        # Call function
        result = create_market_pipeline(mock_state, mock_alerts)
        
        # Assert pipeline was created
        assert result is not None
        mock_pw.io.http.read.assert_called_once()
        mock_table.select.assert_called_once()
        mock_pw.io.jsonlines.write.assert_called_once()
