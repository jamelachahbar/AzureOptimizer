import autogen
import logging
import os

class AutoGenAssistant:
    def __init__(self):
        self.assistant = None
        self.user_proxy = None
        self.setup()

    def setup(self):
        # Load configuration from JSON
        config_list = autogen.config_list_from_json(
            "./OAI_CONFIG_LIST.json"
        )

        # config_list = [
        #     {
        #         "model": os.environ.get("AZURE_OPENAI_MODEL_DEPLOYMENT"),
        #         "api_key": os.environ.get("AZURE_OPENAI_KEY"),
        #         "base_url": os.environ.get("AZURE_OPENAI_ENDPOINT"),
        #         "api_type": "azure",
        #         "api_version": os.environ.get("API_VERSION")
        #     },
        # ]

        # Create an AssistantAgent
        self.assistant = autogen.AssistantAgent(
            name="assistant",
            llm_config={
                "cache_seed": None,  # Seed for caching and reproducibility
                "config_list": config_list,  # List of OpenAI API configurations
                "temperature": 0,  # Temperature for sampling
            },
        )

        # Create a UserProxyAgent
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=5,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={
                "work_dir": "../coding",
                "use_docker": False,  # Consider using Docker for safety
            },
        )

    def initiate_chat(self, prompt):
        # Initiate a chat between the user_proxy and the assistant
        logging.info("Start conversation...")
        chat_res = self.user_proxy.initiate_chat(
            self.assistant,
            message=prompt,
            summary_method="reflection_with_llm",
        )
        logging.info("Conversation ended.")
        return chat_res

# Example usage:   
assistant = AutoGenAssistant()
assistant.initiate_chat("What date is today? Compare the year-to-date gain for MICROSOFT and TESLA.")