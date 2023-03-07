import asyncio
import httpx
import base64
import os
from datetime import datetime
import json

MODEL_ID = "stable-diffusion-v1-5"# prompthero-midjourney-v4-diffusion
with open("config.json") as f:
    config = json.load(f)
API_KEY = config["scenario"]["api_key"]
API_SECRET = config["scenario"]["api_secret"]
api_key_secret = f"{API_KEY}:{API_SECRET}"
authorization_header = base64.b64encode(api_key_secret.encode("utf-8")).decode("utf-8")

result_dir = "./results/"
if not os.path.exists(result_dir):
    os.makedirs(result_dir)

now_models = []

def settle_data(params):
    data = {
        "parameters": {
            "type": "txt2img",
        }
    }
    if params.get("prompt", None) is not None:
        data["parameters"]["prompt"] = ", ".join(params["prompt"])
    if params.get("negative_prompt", None) is not None:
        data["parameters"]["negativePrompt"] = ", ".join(params["negative_prompt"])
    if params.get("steps", None) is not None:
        data["parameters"]["numInferenceSteps"] = params["steps"]
    if params.get("nums", None) is not None:
        data["parameters"]["numSamples"] = params["nums"]
    if params.get("guidance", None) is not None:
        data["parameters"]["guidance"] = params["guidance"]
    return data

async def start_inference(prompt_list, client, params=None):
    prompt = ", ".join(prompt_list)
    data = {
        "parameters": {
            "type": "txt2img",
            "prompt": prompt
        }
    }
    model_id = MODEL_ID
    if params is not None:
        data = settle_data(params)
        model_id = params.get("id", MODEL_ID)
        print(model_id)

    headers = {
        "Authorization": f"Basic {authorization_header}",
        "accept": "application/json",
        "content-type": "application/json"
    }
    response = await client.post(f"https://api.cloud.scenario.gg/v1/models/{model_id}/inferences", headers=headers, json=data)
    if response.status_code != 200:
        print(f"Failed to start inference: {response.json()}")
        return None
    return response.json().get("inference").get("id")

async def get_inference_status(inference_id, client, params):
    headers = {
        "Authorization": f"Basic {authorization_header}",
        "accept": "application/json"
    }
    model_id = MODEL_ID
    if params is not None:
        model_id = params.get("id", MODEL_ID)
    response = await client.get(f"https://api.cloud.scenario.gg/v1/models/{model_id}/inferences/{inference_id}", headers=headers)
    if response.status_code != 200:
        print(f"Failed to get inference status: {response.json()}")
        return "FAILURE"
    result = response.json()
    result = result.get("inference")
    status = result.get("status")
    if status == "in-progress":
        progress = result.get("progress")
        print(f"Inference is in progress: {progress}")
        return None
    elif status == "succeeded":
        images = result.get("images")
        return images
    elif status == "failed":
        print("Inference failed.")
        return None

async def run_inference(prompt_list, save_dir, params):
    async with httpx.AsyncClient() as client:
        inference_id = await start_inference(prompt_list, client, params)
        if inference_id is None:
            return None
        while True:
            images = await get_inference_status(inference_id, client, params)
            if images is not None:
                if images != "FAILURE":
                    download_tasks = [download_image(client, image_info, save_dir) for image_info in images]
                    downloaded_images = await asyncio.gather(*download_tasks)
                    successful_downloads = [image["path"] for image in downloaded_images if "path" in image]
                    return successful_downloads
                else:
                    return None
            await asyncio.sleep(2)

async def get_inference(inference_id):
    async with httpx.AsyncClient() as client:
        while True:
            images = await get_inference_status(inference_id, client)
            if images is not None:
                return images
            await asyncio.sleep(1)

async def download_image(client, image_info, save_dir):
    image_id = image_info["id"]
    image_url = image_info["url"]
    response = await client.get(image_url)
    if response.status_code == 200:
        with open(f"{save_dir}/{image_id}.jpg","wb") as f:
            f.write(response.content)
        return {"id":image_id, "path":f"{save_dir}/{image_id}.jpg"}
    else:
        return {"id":image_id, "error":f"Failed to download image: {response.status_code}"}

def prompt_and_open_folder(params):
    input_str = input('请输入prompts，以逗号分割: ')
    prompt_list = input_str.split(',')
    dir_name = datetime.now().strftime('%Y%m%d_%H%M%S')
    dir_name = os.path.abspath(result_dir+dir_name)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    images = asyncio.run(run_inference(prompt_list, dir_name, params))
    with open(os.path.join(dir_name, 'prompts.txt'), 'w') as f:
        f.write(input_str)
    os.startfile(dir_name)

async def get_images(params):
    dir_name = datetime.now().strftime('%Y%m%d_%H%M%S')
    dir_name = os.path.abspath(result_dir+dir_name)
    if not os.path.exists(dir_name):
        os.makedirs(dir_name)
    images = await run_inference("", dir_name, params)
    with open(os.path.join(dir_name, 'prompts.txt'), 'w') as f:
        f.write(str(params))
    return images

async def get_model():
    async with httpx.AsyncClient() as client:
        headers = {
            "Authorization": f"Basic {authorization_header}",
            "accept": "application/json",
            "content-type": "application/json"
        }
        response = await client.get(f"https://api.cloud.scenario.gg/v1/models?privacy=public&pageSize=50", headers=headers)
        if response.status_code != 200:
            print(f"Failed to start inference: {response.json()}")
            return None
        infos = response.json().get("models")
        models = []
        for info in infos:
            model = {
                "id": info.get("id"),
                "name": info.get("name"),
                "images": info.get("trainingImages"),
            }
            models.insert(0, model)
        global now_models
        now_models = models
        return models

def get_now_models():
    return now_models

if __name__ == '__main__':
    a = asyncio.run(get_model())
