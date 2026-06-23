import logging
import requests
import time
from azure.identity import DefaultAzureCredential
from backend.src.config import settings

logger = logging.getLogger(__name__)


class VideoIndexerService:
    def __init__(self):
        self.video_indexer_name = settings.AZURE_VI_NAME
        self.account_id = settings.AZURE_VI_ACCOUNT_ID
        self.location = settings.AZURE_VI_LOCATION
        self.subscription_id = settings.AZURE_SUBSCRIPTION_ID
        self.resource_group = settings.AZURE_RESOURCE_GROUP
        self.credential = DefaultAzureCredential()

    def get_arm_token(self):
        try:
            token_object = self.credential.get_token(
                "https://management.azure.com/.default"
            )
            return token_object.token
        except Exception as e:
            logger.warning(
                f"DefaultAzureCredential failed. Falling back to AzureCliCredential: {e}"
            )
            from azure.identity import AzureCliCredential

            self.credential = AzureCliCredential()
            token_object = self.credential.get_token(
                "https://management.azure.com/.default"
            )
            return token_object.token

    def get_account_token(self, arm_access_token: str) -> str:
        """Exchange ARM token for a Video Indexer account-scoped access token."""
        url = (
            f"https://management.azure.com/subscriptions/{self.subscription_id}"
            f"/resourceGroups/{self.resource_group}"
            f"/providers/Microsoft.VideoIndexer/accounts/{self.video_indexer_name}"
            f"/generateAccessToken?api-version=2024-01-01"
        )

        headers = {"Authorization": f"Bearer {arm_access_token}"}
        payload = {"permissionType": "Contributor", "scope": "Account"}

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            raise Exception(
                f"Failed to get video indexer account token: {response.text}"
            )

        return response.json()["accessToken"]

    def upload_video_from_url(self, video_url: str, video_name: str) -> str:
        """Upload a video from a URL (e.g., SAS URL) to Azure Video Indexer."""
        arm_token = self.get_arm_token()
        account_token = self.get_account_token(arm_token)

        api_url = (
            f"https://api.videoindexer.ai/{self.location}"
            f"/Accounts/{self.account_id}/Videos"
        )

        params = {
            "accessToken": account_token,
            "name": video_name,
            "videoUrl": video_url,
            "privacy": "Private",
            "indexingPreset": "Default",
        }

        response = requests.post(api_url, params=params)

        if response.status_code != 200:
            raise Exception(f"Failed to upload video from URL: {response.text}")

        return response.json().get("id")

    def process_video(self, video_id: str) -> dict:
        """Poll Azure Video Indexer until the video is processed, then return the full index JSON."""
        while True:
            arm_token = self.get_arm_token()
            account_token = self.get_account_token(arm_token)

            api_url = (
                f"https://api.videoindexer.ai/{self.location}"
                f"/Accounts/{self.account_id}/Videos/{video_id}/Index"
            )
            params = {"accessToken": account_token}

            response = requests.get(api_url, params=params)

            if response.status_code != 200:
                raise Exception(f"Failed to get video index status: {response.text}")

            response_data = response.json()
            state = response_data.get("state", "Unknown")

            if state == "Processed":
                return response_data
            elif state == "Failed":
                raise Exception("Azure Video Indexer failed to process the video.")
            elif state == "Quarantined":
                raise Exception("Video is quarantined (possible copyright violation).")

            logger.info(f"Video indexing status: {state} — waiting 30s…")
            time.sleep(30)

    def extract_insights(self, video_indexer_json: dict, field_name: str) -> str:
        """
        Extract and concatenate text items from a given insight field
        across all video sections in the Video Indexer response.
        """
        videos = video_indexer_json.get("videos", [])
        field_text = []

        for video in videos:
            insights = video.get("insights", {})
            for item in insights.get(field_name, []):
                text = item.get("text")
                if text:
                    field_text.append(text)

        return " ".join(field_text)

    def extract_data(self, video_indexer_json: dict) -> dict:
        """Extract transcript, OCR, and metadata from the Video Indexer response dict."""
        transcript = self.extract_insights(video_indexer_json, "transcript")
        ocr = self.extract_insights(video_indexer_json, "ocr")

        summarized = video_indexer_json.get("summarizedInsights", {})
        duration_seconds = summarized.get("duration", {}).get("seconds", 0)

        return {
            "transcript": transcript,
            "ocr_text": ocr,
            "video_metadata": {
                "duration_seconds": duration_seconds,
                "name": video_indexer_json.get("name", ""),
                "id": video_indexer_json.get("id", ""),
            },
        }
