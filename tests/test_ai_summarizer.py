import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from src.ai.summarizer import Summarizer
from src.ai.exceptions import SummarizationError, APIConnectionError, InvalidResponseError

@pytest.fixture
def summarizer():
    return Summarizer(api_key="test-key")

@pytest.mark.asyncio
async def test_summarize_success(summarizer):
    # Mocking the httpx response
    mock_response_data = {
        "content": [
            {"type": "text", "text": "Line 1: Context\nLine 2: Action\nLine 3: Result"}
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = MagicMock(return_value=mock_response_data)
        mock_post.return_value.text = "OK"

        result = await summarizer.summarize("Some long content")

        assert result == "Line 1: Context\nLine 2: Action\nLine 3: Result"
        assert len(result.split('\n')) == 3

@pytest.mark.asyncio
async def test_summarize_empty_content(summarizer):
    with pytest.raises(SummarizationError, match="Input content is empty"):
        await summarizer.summarize("")

@pytest.mark.asyncio
async def test_summarize_api_failure(summarizer):
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Server Error"

        with pytest.raises(APIConnectionError, match="API request failed with status 500"):
            await summarizer.summarize("Some content")

@pytest.mark.asyncio
async def test_summarize_invalid_format(summarizer):
    mock_response_data = {"wrong_key": "bad_data"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = MagicMock(return_value=mock_response_data)

        with pytest.raises(InvalidResponseError, match="Unexpected API response format"):
            await summarizer.summarize("Some content")

@pytest.mark.asyncio
async def test_summarize_truncates_excess_lines(summarizer):
    mock_response_data = {
        "content": [
            {"type": "text", "text": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"}
        ]
    }

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        mock_post.return_value.json = MagicMock(return_value=mock_response_data)

        result = await summarizer.summarize("Some content", max_lines=3)

        assert len(result.split('\n')) == 3
        assert result == "Line 1\nLine 2\nLine 3"


@pytest.mark.asyncio
async def test_summarize_retries_on_5xx_error(summarizer):
    """Test that the summarizer retries on 5xx errors."""
    call_count = [0]

    def mock_post_side_effect(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] < 3:
            # Return 500 error for first 2 attempts
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            return mock_response
        else:
            # Return success on 3rd attempt
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={
                "content": [{"type": "text", "text": "Success after retry"}]
            })
            return mock_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = mock_post_side_effect

        result = await summarizer.summarize("Some content", max_retries=3)

        assert result == "Success after retry"
        assert call_count[0] == 3


@pytest.mark.asyncio
async def test_summarize_gives_up_after_max_retries(summarizer):
    """Test that the summarizer gives up after max retries."""
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 500
        mock_post.return_value.text = "Internal Server Error"

        with pytest.raises(APIConnectionError, match="API request failed with status 500"):
            await summarizer.summarize("Some content", max_retries=2)

        # Should have been called exactly 2 times (max_retries)
        assert mock_post.call_count == 2