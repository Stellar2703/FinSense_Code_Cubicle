import asyncio
import os
import subprocess
import sys
from typing import Dict, Any, Optional

from .state import AppState
from .alerts import AlertBroker
from .pathway_pipelines import is_available, run_pathway_pipelines


async def integrate_pathway_with_realtime(state: AppState, alerts: AlertBroker) -> bool:
    """
    Integrates Pathway data processing pipelines with the real-time data sources.
    Returns True if Pathway integration was successful, False otherwise.
    """
    if not is_available():
        print("⚠️ Pathway not available, skipping pipeline integration")
        
        # Check if we have a fake/stub version of Pathway instead of the real one
        try:
            import pathway
            if not hasattr(pathway, 'io'):
                print("ℹ️ You have a stub version of Pathway installed.")
                print("   To use real-time data processing features, install the official Pathway package:")
                print("   pip install -U pathway")
        except ImportError:
            print("ℹ️ Pathway is not installed. To install:")
            print("   pip install pathway")
        
        return False
    
    try:
        # Initialize and run Pathway pipelines
        success = run_pathway_pipelines(state, alerts)
        if success:
            print("✅ Pathway pipelines integrated successfully")
            return True
        else:
            print("⚠️ Pathway pipelines initialization failed")
            print("   Check that you have the latest version of Pathway installed:")
            print("   pip install -U pathway")
            return False
    except Exception as e:
        print(f"❌ Pathway integration error: {e}")
        print("   To troubleshoot Pathway issues, visit: https://pathway.com/troubleshooting/")
        return False
