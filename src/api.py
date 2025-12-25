"""Claude API client with retry and caching support."""

import os
import time
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from anthropic import Anthropic, AsyncAnthropic, APIError, RateLimitError, APITimeoutError


class ClaudeAPIClient:
    """Client for Claude API with retry logic and caching."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_retries: int = 3,
        verbose: bool = False,
        log_dir: str = "logs"
    ):
        """
        Initialize Claude API client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            model: Claude model to use
            max_retries: Maximum number of retries for failed requests
            verbose: Enable verbose logging
            log_dir: Directory for API logs
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key not provided. Set ANTHROPIC_API_KEY environment "
                "variable or pass api_key parameter."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)
        self.model = model
        self.max_retries = max_retries
        self.verbose = verbose

        # Setup logging
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.log_file = self.log_dir / "api.log"

    def _log(self, message: str):
        """Log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[API] {message}")

    def _log_api_call(
        self,
        user_message: Dict[str, Any],
        response_text: str,
        status: str = "success"
    ):
        """
        Log API request and response to file.

        Args:
            user_message: User message sent to API
            response_text: Response text from API
            status: Status of the call (success/error)
        """
        timestamp = datetime.now().isoformat()

        log_entry = {
            "timestamp": timestamp,
            "status": status,
            "model": self.model,
            "request": {
                "user_message": user_message
            },
            "response": response_text[:5000]  # Limit response length in log
        }

        # Append to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Status: {status}\n")
            f.write(f"Model: {self.model}\n")
            f.write("-" * 80 + "\n")
            f.write("USER MESSAGE:\n")
            f.write(json.dumps(user_message, indent=2, ensure_ascii=False))
            f.write("\n" + "-" * 80 + "\n")
            f.write("RESPONSE:\n")
            f.write(response_text)
            f.write("\n" + "=" * 80 + "\n\n")

    def _exponential_backoff(self, attempt: int) -> float:
        """
        Calculate exponential backoff delay.

        Args:
            attempt: Current attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        return min(2 ** attempt, 60)  # Max 60 seconds

    def generate_cards(
        self,
        system_message: Dict[str, Any],
        user_message: Dict[str, Any],
        max_tokens: int = 4096
    ) -> str:
        """
        Generate cards using Claude API.

        Args:
            system_message: System message with cache_control
            user_message: User message with input data
            max_tokens: Maximum tokens in response

        Returns:
            Raw response text from Claude

        Raises:
            APIError: If request fails after all retries
        """
        attempt = 0
        last_error = None

        while attempt < self.max_retries:
            try:
                self._log(
                    f"Sending request (attempt {attempt + 1}/{self.max_retries})"
                )

                # Extract system content from message
                system_content = system_message["content"]

                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_content,
                    messages=[user_message]
                )

                # Extract text from response
                if not response.content:
                    raise ValueError("Empty response from API")

                response_text = response.content[0].text

                # Log API call
                self._log_api_call(user_message, response_text, "success")

                # Log cache usage if verbose
                if self.verbose and hasattr(response, 'usage'):
                    usage = response.usage
                    self._log(f"Input tokens: {usage.input_tokens}")
                    self._log(f"Output tokens: {usage.output_tokens}")
                    if hasattr(usage, 'cache_creation_input_tokens'):
                        self._log(
                            f"Cache creation tokens: "
                            f"{usage.cache_creation_input_tokens}"
                        )
                    if hasattr(usage, 'cache_read_input_tokens'):
                        self._log(
                            f"Cache read tokens: "
                            f"{usage.cache_read_input_tokens}"
                        )

                return response_text

            except RateLimitError as e:
                last_error = e
                delay = self._exponential_backoff(attempt)
                self._log(f"Rate limit hit. Retrying in {delay}s...")
                time.sleep(delay)
                attempt += 1

            except APITimeoutError as e:
                last_error = e
                delay = self._exponential_backoff(attempt)
                self._log(f"Request timeout. Retrying in {delay}s...")
                time.sleep(delay)
                attempt += 1

            except APIError as e:
                # Server errors (5xx) - retry
                if hasattr(e, 'status_code') and 500 <= e.status_code < 600:
                    last_error = e
                    delay = self._exponential_backoff(attempt)
                    self._log(
                        f"Server error ({e.status_code}). "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                    attempt += 1
                else:
                    # Client errors (4xx) - don't retry
                    raise

            except Exception as e:
                # Unexpected errors - don't retry
                self._log(f"Unexpected error: {e}")
                raise

        # All retries exhausted
        if last_error:
            raise APIError(
                f"Request failed after {self.max_retries} attempts: "
                f"{last_error}"
            )
        else:
            raise APIError(
                f"Request failed after {self.max_retries} attempts"
            )

    def dry_run(
        self,
        system_message: Dict[str, Any],
        user_message: Dict[str, Any]
    ) -> None:
        """
        Display request without sending it.

        Args:
            system_message: System message
            user_message: User message
        """
        print("=" * 60)
        print("DRY RUN - Request Preview")
        print("=" * 60)
        print(f"\nModel: {self.model}\n")

        print("SYSTEM MESSAGE:")
        print("-" * 60)
        if isinstance(system_message.get("content"), list):
            for item in system_message["content"]:
                if item.get("type") == "text":
                    print(item["text"][:500])  # First 500 chars
                    if len(item["text"]) > 500:
                        print(f"\n... ({len(item['text']) - 500} more chars)")
        print()

        print("USER MESSAGE:")
        print("-" * 60)
        print(user_message.get("content", ""))
        print("\n" + "=" * 60 + "\n")
