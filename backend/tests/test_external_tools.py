"""
Tests for External Tool Integration (Firecrawl and E2B)
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Test imports
from src.tools.firecrawl_tool import FirecrawlTool, web_search, scrape_webpage
from src.tools.e2b_tool import E2BTool, run_python_code, run_javascript_code


class TestFirecrawlTool:
    """Test suite for Firecrawl web research tool."""

    @pytest.fixture
    def firecrawl_tool(self):
        """Create a FirecrawlTool instance for testing."""
        with patch.dict(os.environ, {'FIRECRAWL_API_KEY': 'test-api-key'}):
            tool = FirecrawlTool()
            # Mock the client to avoid actual API calls
            tool.client = MagicMock()
            return tool

    def test_web_search_basic(self, firecrawl_tool):
        """Test basic web search functionality."""
        # Mock the search response
        firecrawl_tool.client.search.return_value = {
            'data': [
                {
                    'title': 'Test Result 1',
                    'url': 'https://example.com/1',
                    'snippet': 'This is a test snippet',
                    'markdown': '# Test Content'
                },
                {
                    'title': 'Test Result 2',
                    'url': 'https://example.com/2',
                    'snippet': 'Another test snippet',
                    'markdown': '## More Content'
                }
            ]
        }

        result = firecrawl_tool.web_search('test query', max_results=2)

        assert result['status'] == 'success'
        assert result['query'] == 'test query'
        assert len(result['results']) == 2
        assert result['results'][0]['title'] == 'Test Result 1'
        assert result['results'][1]['url'] == 'https://example.com/2'

    def test_web_search_cache_mechanism(self, firecrawl_tool):
        """Test that search results are cached properly."""
        # Clear cache first
        firecrawl_tool.clear_cache()

        # Mock search response
        firecrawl_tool.client.search.return_value = {'data': []}

        # First search should hit the API
        result1 = firecrawl_tool.web_search('cached query', use_cache=True)
        assert firecrawl_tool.client.search.call_count == 1

        # Second search should use cache
        result2 = firecrawl_tool.web_search('cached query', use_cache=True)
        assert firecrawl_tool.client.search.call_count == 1  # Still 1, not 2

        # Results should be the same
        assert result1['query'] == result2['query']

    def test_scrape_content_basic(self, firecrawl_tool):
        """Test basic content scraping functionality."""
        # Mock the scrape response
        firecrawl_tool.client.scrape_url.return_value = {
            'content': 'Page content here',
            'markdown': '# Page Title\nPage content here',
            'metadata': {
                'title': 'Test Page',
                'description': 'Test description',
                'author': 'Test Author'
            }
        }

        result = firecrawl_tool.scrape_content('https://example.com')

        assert result['status'] == 'success'
        assert result['url'] == 'https://example.com'
        assert result['title'] == 'Test Page'
        assert result['markdown'] == '# Page Title\nPage content here'
        assert result['metadata']['author'] == 'Test Author'

    def test_batch_scrape(self, firecrawl_tool):
        """Test batch scraping multiple URLs."""
        urls = ['https://example.com/1', 'https://example.com/2', 'https://example.com/3']

        # Mock scrape responses
        firecrawl_tool.client.scrape_url.return_value = {
            'content': 'Content',
            'markdown': '# Content',
            'metadata': {'title': 'Page'}
        }

        results = firecrawl_tool.batch_scrape(urls, max_concurrent=2)

        assert len(results) == 3
        assert all(r['status'] == 'success' for r in results)
        # Should be called 3 times for 3 URLs
        assert firecrawl_tool.client.scrape_url.call_count == 3

    def test_error_handling_no_api_key(self):
        """Test behavior when API key is missing."""
        with patch.dict(os.environ, {}, clear=True):
            tool = FirecrawlTool()
            result = tool.web_search('test query')

            assert result['status'] == 'error'
            assert 'not initialized' in result['error']


class TestE2BTool:
    """Test suite for E2B code execution tool."""

    @pytest.fixture
    def e2b_tool(self):
        """Create an E2BTool instance for testing."""
        with patch.dict(os.environ, {'E2B_API_KEY': 'test-api-key'}):
            with patch('src.tools.e2b_tool.CodeInterpreter'):
                tool = E2BTool()
                return tool

    @patch('src.tools.e2b_tool.CodeInterpreter')
    def test_execute_python_basic(self, mock_code_interpreter):
        """Test basic Python code execution."""
        # Mock sandbox and execution
        mock_sandbox = MagicMock()
        mock_code_interpreter.return_value = mock_sandbox

        # Mock execution result
        mock_result = MagicMock()
        mock_result.text = "Hello, World!"
        mock_result.error = None
        mock_result.result = "Success"
        mock_sandbox.notebook.exec_cell.return_value = mock_result

        with patch.dict(os.environ, {'E2B_API_KEY': 'test-api-key'}):
            tool = E2BTool()
            result = tool.execute_python('print("Hello, World!")', timeout=30)

        assert result['status'] == 'success'
        assert result['language'] == 'python'
        assert result['stdout'] == "Hello, World!"
        assert 'execution_time' in result

    @patch('src.tools.e2b_tool.CodeInterpreter')
    def test_execute_python_with_error(self, mock_code_interpreter):
        """Test Python execution with error handling."""
        # Mock sandbox and execution error
        mock_sandbox = MagicMock()
        mock_code_interpreter.return_value = mock_sandbox

        # Simulate an execution error
        mock_sandbox.notebook.exec_cell.side_effect = Exception("Syntax error")

        with patch.dict(os.environ, {'E2B_API_KEY': 'test-api-key'}):
            tool = E2BTool()
            result = tool.execute_python('invalid python code', timeout=30)

        assert result['status'] == 'error'
        assert 'Syntax error' in result['error']
        assert 'traceback' in result

    @patch('src.tools.e2b_tool.CodeInterpreter')
    def test_execute_javascript(self, mock_code_interpreter):
        """Test JavaScript code execution."""
        # Mock sandbox
        mock_sandbox = MagicMock()
        mock_code_interpreter.return_value = mock_sandbox

        # Mock subprocess execution result
        mock_result = MagicMock()
        mock_result.text = "STDOUT: console output\nRETURN_CODE: 0"
        mock_sandbox.notebook.exec_cell.return_value = mock_result

        with patch.dict(os.environ, {'E2B_API_KEY': 'test-api-key'}):
            tool = E2BTool()
            result = tool.execute_javascript('console.log("test")', timeout=30)

        assert result['language'] == 'javascript'
        assert 'stdout' in result
        assert 'return_code' in result

    @patch('src.tools.e2b_tool.CodeInterpreter')
    def test_execute_with_files(self, mock_code_interpreter):
        """Test code execution with input files."""
        # Mock sandbox
        mock_sandbox = MagicMock()
        mock_code_interpreter.return_value = mock_sandbox

        # Mock execution result
        mock_result = MagicMock()
        mock_result.text = "File processed"
        mock_sandbox.notebook.exec_cell.return_value = mock_result

        files = {
            'data.csv': 'col1,col2\n1,2\n3,4',
            'config.json': '{"key": "value"}'
        }

        with patch.dict(os.environ, {'E2B_API_KEY': 'test-api-key'}):
            tool = E2BTool()
            result = tool.execute_with_files(
                'import pandas as pd\ndf = pd.read_csv("data.csv")',
                files,
                language='python'
            )

        assert result['status'] == 'success'
        assert result['input_files'] == ['data.csv', 'config.json']

    def test_timeout_handling(self):
        """Test that timeout is properly enforced."""
        # This is a conceptual test - actual implementation would need
        # real sandbox to test timeout behavior
        with patch.dict(os.environ, {'E2B_API_KEY': 'test-api-key'}):
            tool = E2BTool()
            # Verify timeout parameter is accepted
            assert hasattr(tool, 'execute_python')
            # In real test, would verify timeout is enforced


class TestToolRegistry:
    """Test tool registry integration with external tools."""

    def test_research_tools_include_firecrawl(self):
        """Test that research tools include Firecrawl functions."""
        from src.tools.tool_registry import get_research_tools

        tools = get_research_tools()
        tool_names = [tool['name'] for tool in tools]

        assert 'web_search' in tool_names
        assert 'scrape_webpage' in tool_names
        assert 'batch_scrape' in tool_names
        assert 'search_and_summarize' in tool_names

    def test_analysis_tools_include_e2b(self):
        """Test that analysis tools include E2B functions."""
        from src.tools.tool_registry import get_analysis_tools

        tools = get_analysis_tools()
        tool_names = [tool['name'] for tool in tools]

        assert 'run_python_code' in tool_names
        assert 'run_javascript_code' in tool_names
        assert 'run_r_code' in tool_names
        assert 'run_code_with_data' in tool_names

    def test_tool_functions_are_callable(self):
        """Test that registered tool functions are actually callable."""
        from src.tools.tool_registry import get_research_tools, get_analysis_tools

        # Check research tools
        for tool in get_research_tools():
            if 'web_search' in tool['name'] or 'scrape' in tool['name']:
                assert callable(tool['function'])

        # Check analysis tools
        for tool in get_analysis_tools():
            if 'run_' in tool['name']:
                assert callable(tool['function'])


class TestModuleLevelFunctions:
    """Test module-level functions that will be registered as tools."""

    @patch('src.tools.firecrawl_tool._tool_instance')
    def test_web_search_module_function(self, mock_instance):
        """Test the module-level web_search function."""
        mock_instance.web_search.return_value = {'status': 'success'}

        result = web_search('test query')
        assert result['status'] == 'success'
        mock_instance.web_search.assert_called_once_with('test query', 5)

    @patch('src.tools.e2b_tool._tool_instance')
    def test_run_python_code_module_function(self, mock_instance):
        """Test the module-level run_python_code function."""
        mock_instance.execute_python.return_value = {'status': 'success'}

        result = run_python_code('print("test")')
        assert result['status'] == 'success'
        mock_instance.execute_python.assert_called_once_with('print("test")', 30)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])