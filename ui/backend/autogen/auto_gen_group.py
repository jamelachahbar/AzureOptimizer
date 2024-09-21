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
            system_message="""You are the planner of this team of assistants. You plan the tasks and make sure everything is on track. Suggest a plan. Revise the plan based on feedback from user_proxy and get his approval.
            The plan involves the Code_Guru who can write code. Share the plan first to the Code_Guru and he creates code only, saves it to a file with the name code_guru in it, user_proxy will execute it on behalf of the user if permitted.""",
            llm_config=llm_config
        )

        # Create UserProxyAgent
        self.user_proxy = autogen.UserProxyAgent(
            name="user_proxy",
            human_input_mode="ALWAYS",
            max_consecutive_auto_reply=10,
            code_execution_config={
                "work_dir": "../coding",
                "use_docker": "python:3.11"
            },
            system_message="""Reply TERMINATE if the task has been solved at full satisfaction.
            Otherwise, reply CONTINUE, or the reason why the task has not been solved yet. Make sure you are not running dummy or placeholder code.
            If you get a summary_output.csv file, read the file and display the content. If not, output the results in summary_output.csv or append it if content is not the same.""",
            description="I am the user proxy. I am the interface between the user and the assistants. I can run code to help the assistants. If I run into issues like unknown language kusto, I will ask for help and jointly we'll try to solve the issue.",
            function_map={"ask_planner": self.ask_planner}
        )

        # Create an AssistantAgent for coding
        # self.coder = autogen.AssistantAgent(
        #     name="Code_Guru",
        #     system_message="""You are a highly experienced programmer specialized in Azure. Trying to generate an Azure Resource Graph query for the intent, infered from the prompt.
        #     only use the functions you have been provided with. 
        #     "reply with helpful tips. Once you've recommended functions"
        #     "reply with 'TERMINATE'.",""",
        #     llm_config=llm_config,
        #     function_map={
        #         "run_kusto_query": run_kusto_query  # Ensure this is linked correctly
        #     },            
        #     human_input_mode="ALWAYS",
        # )
        # Create an AssistantAgent for coding with external KQL handling
        self.coder = autogen.AssistantAgent(
            name="Code_Guru",
            # """Given the problem and solution, use the functions you have been provided with. Make sure the code will actually work. Do not execute any code yourself.
            # Test and write the code to a file called code_guru.py and reply with 'TERMINATE'.""",
            system_message=""" You are a highly experienced programmer specialized in Azure. 
            If you see a request to get data from the environment, you can run Kusto queries to do resource analysis, use the 'run_kusto_query' function to query Azure Resource Graph. 
            Do not directly write the kusto query but wrap it around bash or python. No powershell please!""",
            description="I am a highly experienced programmer specialized in Azure. I am **ONLY** allowed to speak **immediately** after `Planner`",
            llm_config={
                "cache_seed": None,  # Seed for caching and reproducibility
                "config_list": config_list,  # List of OpenAI API configurations
                "temperature": 0  # Temperature for sampling
            },
            human_input_mode="NEVER",
            function_map={
                "run_kusto_query": run_kusto_query  # Ensure this is linked correctly
            }            
        )

        # Create an AssistantAgent for FinOps
        self.finops_expert = autogen.AssistantAgent(
            name="Finops_Expert",
            system_message="You are an Azure Expert specialized in FinOps and Azure Cost Optimization. You provide the highest level of expertise in FinOps and Azure Cost Optimization Don't give any programming advice or code advice.",
            llm_config=llm_config,
            human_input_mode="NEVER"
        )

        # Create the GroupChat and GroupChatManager
        self.groupchat = autogen.GroupChat(agents=
                                           [self.planner, self.coder, self.user_proxy], 
                                               messages=[10], max_round=10, 
                                                speaker_selection_method="round_robin"
                                              )
        self.manager = autogen.GroupChatManager(groupchat=self.groupchat, llm_config=llm_config)
    
    
    def run_kusto_query(self, query):
        """Function to run KQL queries using Azure CLI or SDK."""
        return run_kusto_query(query)

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
            summary_method="reflection_with_llm"

        )
        logging.info("Conversation ended.")
        return chat_res
