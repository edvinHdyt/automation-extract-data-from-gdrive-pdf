import os
from dotenv import load_dotenv
os.environ["HF_HOME"] = "D:/Web-Devel/Python/huggingface_cache"
load_dotenv()
from huggingface_hub import login
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from utils.LoggerTrait import LoggerTrait

class ModelConn(LoggerTrait):
    modelId:str
    hf_token = os.getenv("HF_TOKEN")
    model: AutoModelForCausalLM
    tokenizer: AutoTokenizer
    
    def __init__(self, modelId:str):
        self.modelId = modelId

        if self.hf_token:
            login(token=self.hf_token)
        else:
            self.logger.error("HF Token tidak ada!")
            raise Exception("HF Token tidak ada!")

        self.tokenizer = AutoTokenizer.from_pretrained(modelId)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.modelId,
            device_map="cuda"
        )
