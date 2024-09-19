import logging
import autogen
from kusto_utils import run_kusto_query  # Import the function from the separate module

class AutoGenGroup:
    def __init__(self):
        self.assistant = None
        self.user_proxy = None
        self.planner = None
        self.setup()

    def setup(self):
        # Load configuration from JSON
        config_list = autogen.config_list_from_json("./OAI_CONFIG_LIST.json")
        llm_config = {"config_list": config_list, "cache_seed": 0}

        # Initialize the Planner
        self.planner = autogen.AssistantAgent(
            name="Planner",
            system_message="You are the planner of this team of assistants. You plan the tasks and make sure everything is on track.",
            llm_config=llm_config
        )

        # Create UserProxyAgent
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="NEVER",
            max_consecutive_auto_reply=10,
            code_execution_config={
                "work_dir": "../coding",
                "use_docker": False,
            },
            function_map={"ask_planner": self.ask_planner}
        )

        # Create an AssistantAgent for coding
        self.coder = autogen.AssistantAgent(
            name="Code_Guru",
            system_message=""" You are a highly experienced programmer specialized in Azure. 
            If you see a request to get data from the environment, you can run Kusto queries to do resource analysis, use the 'run_kusto_query' function to query Azure Resource Graph. 
            Do not directly write the kusto query but wrap it around bash or python. No powershell please!""",
            llm_config=llm_config,
            function_map={
                "run_kusto_query": run_kusto_query  # Ensure this is linked correctly
            },            
            human_input_mode="ALWAYS",
        )


        # Create an AssistantAgent for FinOps
        self.finops_expert = autogen.AssistantAgent(
            name="Finops_Expert",
            system_message="You are an Azure Expert specialized in FinOps and Azure Cost Optimization. You provide the highest level of expertise in FinOps and Azure Cost Optimization Don't give any programming advice or code advice.",
            llm_config=llm_config,
            human_input_mode="NEVER"
        )

        # Create the GroupChat and GroupChatManager
        self.groupchat = autogen.GroupChat(agents=[self.user_proxy, self.coder, self.finops_expert, self.planner], messages=[], max_round=10)
        self.manager = autogen.GroupChatManager(groupchat=self.groupchat, llm_config=llm_config)

    def ask_planner(self, message):
        """A placeholder ask_planner method for testing."""
        logging.info(f"Planner received the following message: {message}")
        return f"Planner response to: {message}"

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
