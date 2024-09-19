import autogen
import logging

class AutoGenGroup:
    def __init__(self):
        self.assistant = None
        self.user_proxy = None
        self.setup()

    def setup(self):
        # Load configuration from JSON
        config_list = autogen.config_list_from_json(
            "./OAI_CONFIG_LIST.json"
        )

        llm_config = {"config_list": config_list, "cache_seed": 42}


        # Create a UserProxyAgent
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
            code_execution_config={
                "work_dir": "../coding",
                "use_docker": False,  # Consider using Docker for safety
            },
        )

        # Create an AssistantAgent
        self.coder = autogen.AssistantAgent(
            name="Code_Guru",
            system_message="You are a highly experienced programmer specialized in Azure, being able to use Azure CLI and Powershell to accomplish a set of instructions through code. You are a kisto query language wizard and can use it to query anything in Azure. You also know everything about the Azure cost api, and use a combination of all these tools to help the customers",
            llm_config={
                "cache_seed": None,  # Seed for caching and reproducibility
                "config_list": config_list,  # List of OpenAI API configurations
                "temperature": 0,  # Temperature for sampling

            },
            human_input_mode="NEVER",
        )

        self.finops_expert = autogen.AssistantAgent(
            name="Finops_Expert",
            system_message="You are an Azure Expert specialized in finops. You are able to give concrete and safe recommendations to improve the finops in Azure environments to programmers. https://learn.microsoft.com/en-us/azure/advisor/advisor-reference-cost-recommendations, https://learn.microsoft.com/en-us/azure/well-architected/cost-optimization/principles#design-for-usage-optimization",
            llm_config=llm_config,
            human_input_mode="NEVER"
        )

        self.groupchat = autogen.GroupChat(agents=[self.user_proxy, self.coder, self.finops_expert], messages=[], max_round=5)
        self.manager = autogen.GroupChatManager(groupchat=self.groupchat, llm_config=llm_config)


    def initiate_chat(self, prompt):
        # Initiate a chat between the user_proxy and the assistant
        logging.info("Start conversation...")
        chat_res = self.user_proxy.initiate_chat(
            self.manager,
            message=prompt,
            summary_method="reflection_with_llm",
        )
        logging.info("Conversation ended.")
        return chat_res
