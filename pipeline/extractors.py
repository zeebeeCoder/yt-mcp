import json
import subprocess
import time
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from googleapiclient.discovery import build
from tenacity import retry, stop_after_attempt, wait_exponential
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled
import yt_dlp

from models.schemas import Comment, CommentsData, TranscriptData, VideoMetadata
from utils.logging import get_logger

logger = get_logger(__name__)


class YouTubeExtractor:
    """YouTube data extraction client"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def extract_video_id(self, video_url: str) -> str:
        """Extract video ID from YouTube URL with robust parsing"""
        import re
        
        # Clean up escaped characters that might come from shell/copy-paste
        clean_url = video_url.replace("\\?", "?").replace("\\&", "&").replace("\\=", "=")
        
        # Handle various YouTube URL formats
        patterns = [
            r'(?:v=|/)([0-9A-Za-z_-]{11}).*',  # Standard and shortened URLs
            r'(?:embed/)([0-9A-Za-z_-]{11}).*',  # Embed URLs
            r'(?:watch\?.*v=)([0-9A-Za-z_-]{11}).*',  # Watch URLs with parameters
        ]
        
        for pattern in patterns:
            match = re.search(pattern, clean_url)
            if match:
                video_id = match.group(1)
                logger.info(f"Extracted video ID '{video_id}' from URL: {video_url}")
                return video_id
        
        # Fallback to original parsing method
        try:
            parsed_url = urlparse(clean_url)
            video_id = parse_qs(parsed_url.query).get("v")
            if video_id:
                return video_id[0]
        except Exception as e:
            logger.warning(f"Fallback URL parsing failed: {e}")
        
        raise ValueError(f"Could not extract video ID from URL: {video_url}")
    

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_video_metadata(self, video_id: str) -> VideoMetadata:
        """Fetch video metadata from YouTube API"""
        logger.info(f"Fetching metadata for video: {video_id}")

        request = self.youtube.videos().list(part="snippet", id=video_id)
        response = request.execute()

        items = response.get("items", [])
        if not items:
            raise ValueError(f"Video not found: {video_id}")

        video_data = items[0]["snippet"]

        return VideoMetadata(
            video_id=video_id,
            title=video_data["title"],
            author=video_data["channelTitle"],
            channel_title=video_data["channelTitle"],
            published_date=datetime.fromisoformat(video_data["publishedAt"].replace("Z", "+00:00")),
            url=f"https://www.youtube.com/watch?v={video_id}"
        )

    def fetch_transcript(self, video_id: str) -> TranscriptData:
        """Fetch video transcript using YT-DLP (primary) with youtube-transcript-api fallback"""
        logger.info(f"Fetching transcript for video: {video_id}")

        # Method 1: Try YT-DLP first (more reliable)
        try:
            logger.info("Attempting transcript extraction using YT-DLP...")
            transcript_text = self._extract_transcript_with_ytdlp(video_id)
            if transcript_text:
                word_count = len(transcript_text.split())
                char_count = len(transcript_text)
                # Rough token estimate (1 token ≈ 4 characters for English)
                estimated_tokens = char_count // 4
                
                logger.info(f"YT-DLP transcript extracted successfully:")
                logger.info(f"  - Character count: {char_count:,}")
                logger.info(f"  - Word count: {word_count:,}")
                logger.info(f"  - Estimated tokens: {estimated_tokens:,}")
                
                return TranscriptData(
                    text=transcript_text,
                    word_count=word_count,
                    available=True,
                    language="yt-dlp"
                )
        except Exception as e:
            logger.warning(f"YT-DLP transcript extraction failed: {e}")

        # Method 2: Fallback to youtube-transcript-api
        try:
            logger.info("Falling back to youtube-transcript-api...")
            transcript_data = YouTubeTranscriptApi.get_transcript(video_id)
            transcript_text = " ".join([item["text"] for item in transcript_data])
            
            word_count = len(transcript_text.split())
            char_count = len(transcript_text)
            estimated_tokens = char_count // 4
            
            logger.info(f"YouTube-API transcript extracted successfully:")
            logger.info(f"  - Character count: {char_count:,}")
            logger.info(f"  - Word count: {word_count:,}")
            logger.info(f"  - Estimated tokens: {estimated_tokens:,}")
            logger.info(f"  - Transcript segments: {len(transcript_data):,}")

            return TranscriptData(
                text=transcript_text,
                word_count=word_count,
                available=True,
                language="youtube-api"
            )

        except TranscriptsDisabled:
            logger.warning(f"Transcripts disabled for video: {video_id}")
            return TranscriptData(
                text=None,
                word_count=0,
                available=False,
                error_message="Transcripts are disabled for this video"
            )

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"YouTube-transcript-api also failed: {error_msg}")

            # Method 3: Try alternative languages with youtube-transcript-api
            if "No transcripts were found" in error_msg:
                try:
                    logger.info("Trying alternative languages...")
                    transcript_data = YouTubeTranscriptApi.get_transcript(
                        video_id, languages=["en", "pl", "auto"]
                    )
                    transcript_text = " ".join([item["text"] for item in transcript_data])

                    return TranscriptData(
                        text=transcript_text,
                        word_count=len(transcript_text.split()),
                        available=True,
                        language="alternative"
                    )
                except Exception as alt_e:
                    logger.error(f"Alternative transcript fetch also failed: {alt_e}")

            return TranscriptData(
                text=None,
                word_count=0,
                available=False,
                error_message=f"All transcript extraction methods failed. YT-DLP: failed, YouTube-API: {error_msg}"
            )

    def _extract_transcript_with_ytdlp(self, video_id: str) -> str:
        """Extract transcript using YT-DLP"""
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        # Configure YT-DLP options
        ydl_opts = {
            'writesubtitles': True,
            'writeautomaticsub': True,
            'skip_download': True,  # Don't download video, just subtitles
            'subtitleslangs': ['en', 'en-US', 'en-GB'],  # Prefer English
            'subtitlesformat': 'ttml/vtt/srv1/srv2/srv3',  # Multiple formats
            'quiet': True,  # Suppress output
            'no_warnings': True,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Get video info including available subtitles
                info = ydl.extract_info(video_url, download=False)
                
                # Check for manual subtitles first (higher quality)
                if info.get('subtitles'):
                    for lang in ['en', 'en-US', 'en-GB']:
                        if lang in info['subtitles']:
                            subtitle_info = info['subtitles'][lang][0]
                            subtitle_url = subtitle_info['url']
                            return self._download_and_parse_subtitle(subtitle_url)
                
                # Fall back to automatic captions
                if info.get('automatic_captions'):
                    for lang in ['en', 'en-US', 'en-GB']:
                        if lang in info['automatic_captions']:
                            subtitle_info = info['automatic_captions'][lang][0]
                            subtitle_url = subtitle_info['url']
                            return self._download_and_parse_subtitle(subtitle_url)
                
                logger.warning(f"No subtitles found for video {video_id}")
                return ""
                
        except Exception as e:
            logger.error(f"YT-DLP extraction failed for {video_id}: {e}")
            raise

    def _download_and_parse_subtitle(self, subtitle_url: str) -> str:
        """Download and parse subtitle content from URL"""
        try:
            # Use YT-DLP to download subtitle content
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download subtitle content
                subtitle_content = ydl.urlopen(subtitle_url).read().decode('utf-8')
                
                # Parse different subtitle formats
                if '<tt xml:lang=' in subtitle_content or '<transcript>' in subtitle_content:
                    # TTML format
                    return self._parse_ttml_content(subtitle_content)
                elif 'WEBVTT' in subtitle_content:
                    # WebVTT format
                    return self._parse_webvtt_content(subtitle_content)
                else:
                    # Try to extract text from other formats
                    import re
                    # Simple regex to extract text content
                    text_content = re.sub(r'<[^>]+>', '', subtitle_content)
                    text_content = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}', '', text_content)
                    return ' '.join(text_content.split())
                    
        except Exception as e:
            logger.error(f"Failed to download/parse subtitle: {e}")
            raise

    def _parse_ttml_content(self, content: str) -> str:
        """Parse TTML subtitle content"""
        import re
        # Extract text from <p> tags
        text_matches = re.findall(r'<p[^>]*>(.*?)</p>', content, re.DOTALL)
        text_parts = []
        for match in text_matches:
            # Remove any remaining XML tags
            clean_text = re.sub(r'<[^>]+>', ' ', match)
            clean_text = clean_text.strip()
            if clean_text:
                text_parts.append(clean_text)
        return ' '.join(text_parts)

    def _parse_webvtt_content(self, content: str) -> str:
        """Parse WebVTT subtitle content"""
        lines = content.split('\n')
        text_parts = []
        
        for line in lines:
            line = line.strip()
            # Skip headers, timestamps, and empty lines
            if (line.startswith('WEBVTT') or 
                line.startswith('NOTE') or
                '-->' in line or 
                not line or
                line.startswith('STYLE') or
                line.startswith('Kind:')):
                continue
            text_parts.append(line)
        
        return ' '.join(text_parts)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_comments(self, video_id: str, max_comments: int = 5000, max_total_word_length: int = 80000) -> CommentsData:
        """Fetch video comments from YouTube API with pagination"""
        logger.info(f"Fetching comments for video: {video_id} (max: {max_comments})")

        comments = []
        page_token = None
        total_word_count = 0

        while len(comments) < max_comments and total_word_count < max_total_word_length:
            try:
                request = self.youtube.commentThreads().list(
                    part="snippet,replies",
                    videoId=video_id,
                    textFormat="plainText",
                    pageToken=page_token,
                    maxResults=min(100, max_comments - len(comments))
                )

                response = request.execute()
                comments_data = response.get("items", [])

                for item in comments_data:
                    comment_snippet = item["snippet"]["topLevelComment"]["snippet"]
                    comment_text = comment_snippet["textDisplay"]
                    comment_word_count = len(comment_text.split())

                    # Check word limit
                    if total_word_count + comment_word_count > max_total_word_length:
                        logger.info(f"Reached word limit ({max_total_word_length}), stopping comment collection")
                        break

                    # Extract replies if present
                    replies = []
                    if "replies" in item:
                        replies = [
                            reply["snippet"]["textDisplay"]
                            for reply in item["replies"]["comments"]
                        ]

                    comment = Comment(
                        comment=comment_text,
                        user_name=comment_snippet["authorDisplayName"],
                        date=datetime.fromisoformat(comment_snippet["publishedAt"].replace("Z", "+00:00")),
                        like_count=comment_snippet["likeCount"],
                        replies=replies
                    )

                    comments.append(comment)
                    total_word_count += comment_word_count

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

                # Add small delay to avoid rate limiting
                time.sleep(0.1)

            except Exception as e:
                logger.error(f"Error fetching comments: {e}")
                break

        logger.info(f"Collected {len(comments)} comments with {total_word_count} total words")

        return CommentsData(
            comments=comments,
            total_count=len(comments),
            processed_count=len(comments),
            total_word_count=total_word_count
        )
