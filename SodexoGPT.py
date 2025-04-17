import openai
import os
from dotenv import load_dotenv
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class AzureOpenAIClient:
    def __init__(self):
        """Initialize Azure OpenAI client with secure credentials"""
        self.configure_client()
        self.deployment_name = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4-mini")
        logger.info("Azure OpenAI client initialized")

    def configure_client(self):
        """Configure the OpenAI client with Azure settings"""
        required_vars = [
            "AZURE_OPENAI_ENDPOINT",
            "AZURE_OPENAI_KEY",
            "AZURE_OPENAI_API_VERSION"
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

        openai.api_type = "azure"
        openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
        openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2023-03-15-preview")
        openai.api_key = os.getenv("AZURE_OPENAI_KEY")

    def get_chat_completion(self, messages: list, max_tokens: int = 100) -> str:
        """Get completion from Azure OpenAI model"""
        try:
            response = openai.ChatCompletion.create(
                engine=self.deployment_name,
                messages=messages,
                max_tokens=max_tokens
            )
            return response['choices'][0]['message']['content'].strip()
        except Exception as e:
            logger.error(f"Error in Azure OpenAI request: {str(e)}")
            raise

def main():
    try:
        # Initialize client
        client = AzureOpenAIClient()

        # Example conversation
        messages = [
            {"role": "system", "content": "You are a helpful assistant that provides concise answers."},
            {"role": "user", "content": "Suggest 3 creative names for a tech startup in the AI sector"}
        ]

        # Get response
        print("Making request to Azure OpenAI...")
        response = client.get_chat_completion(messages, max_tokens=150)
        
        print("\nResponse from Azure OpenAI:")
        print(response)

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
