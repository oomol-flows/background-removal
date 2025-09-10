#region generated meta
import typing
class Inputs(typing.TypedDict):
    image_url: str
    output_file: str | None
class Outputs(typing.TypedDict):
    image: str
#endregion

import os
import requests
import json
from oocana import Context
import tempfile
import time
import time


def main(params: Inputs, context: Context) -> Outputs:
    """
    Main function to remove background from an image using FAL API.
    
    Args:
        params: Input parameters containing the file path
        context: OOMOL context object for environment variables and preview
        
    Returns:
        Outputs: Dictionary containing the path to the processed image
    """
    
    # Get API configuration from environment
    console_api_url = context.oomol_llm_env.get("base_url")
    api_key = context.oomol_llm_env.get("api_key")
    
    try:
        # Step 1: Start background removal task
        start_url = console_api_url + "/api/tasks/fal/images/background-remove/start"
        
        image_input = params["image_url"]
        
        # Check if input is a URL or file path
        if image_input.startswith(('http://', 'https://')):
            # Handle URL input
            data = {'image_url': image_input}
            headers = {
                'Authorization': api_key,
                'Content-Type': 'application/json'
            }
            response: Response = requests.post(start_url, json=data, headers=headers, timeout=120)
        else:
            # Handle file path input
            if not os.path.exists(image_input):
                raise FileNotFoundError(f"Image file not found: {image_input}")
                
            # Upload file as multipart/form-data
            with open(image_input, 'rb') as f:
                files = {'image_url': f}
                headers = {
                    'Authorization': api_key
                }
                response: Response = requests.post(start_url, files=files, headers=headers, timeout=120)
        
        response.raise_for_status()
        
        # Parse JSON response to get request_id
        result_data = response.json()
        
        # Validate response structure
        if 'request_id' not in result_data:
            raise ValueError("Invalid API response format: missing 'request_id'")
        
        request_id = result_data['request_id']
        if not isinstance(request_id, str):
            raise ValueError("Invalid request_id format")
        
        print(f"Task started successfully. Request ID: {request_id}")
        
        # Step 2: Poll task status until completion
        status_url = console_api_url + f"/api/tasks/fal/images/background-remove/status/{request_id}"
        
        max_attempts = 30  # Maximum polling attempts
        poll_interval = 5  # Poll every 5 seconds
        
        for attempt in range(max_attempts):
            status_response = requests.get(status_url, headers=headers, timeout=30)
            status_response.raise_for_status()
            
            status_data = status_response.json()
            
            if 'data' not in status_data or 'status' not in status_data['data']:
                raise ValueError("Invalid status response format")
            
            task_status = status_data['data']['status']
            
            if task_status == 'COMPLETED':
                print("Task completed successfully")
                break
            elif task_status == 'FAILED':
                raise Exception("Background removal task failed")
            elif task_status == 'IN_PROGRESS':
                print(f"Task is running... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(poll_interval)
            else:
                raise ValueError(f"Unknown task status: {task_status}")
        else:
            raise Exception("Task timeout - maximum polling attempts reached")
        
        # Step 3: Get task result
        result_url = console_api_url + f"/api/tasks/fal/images/background-remove/result/{request_id}"
        
        result_response = requests.get(result_url, headers=headers, timeout=60)
        result_response.raise_for_status()
        
        result_data = result_response.json()
        
        # Validate result structure
        if 'data' not in result_data or 'image' not in result_data['data']:
            raise ValueError("Invalid result response format: missing 'data.image'")
        
        image = result_data['data']['image']
        if not isinstance(image, dict) or 'url' not in image:
            raise ValueError("Invalid result response format: image should be an object with 'url' field")
        
        # Extract image URL
        image_url = image['url']
        if not isinstance(image_url, str) or not image_url.startswith('http'):
            raise ValueError(f"Invalid image URL: {image_url}")
        
        # Download the processed image from the image URL
        image_download_response = requests.get(image_url, timeout=60)
        image_download_response.raise_for_status()
        
        print(f"Successfully retrieved image from: {image_url}")
        
        # Save image to local file
        output_file_path = params.get("output_file")
        
        if output_file_path:
            # Use provided output file path
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'wb') as f:
                f.write(image_download_response.content)
            saved_file_path = output_file_path
        else:
            # Use temporary file as fallback
            file_extension = os.path.splitext(image_url)[1] or '.png'
            if len(file_extension) > 4:  # Handle cases where extension might be too long
                file_extension = '.png'
            temp_file = tempfile.NamedTemporaryFile(
                suffix=file_extension, 
                delete=False,
                dir="/oomol-driver/oomol-storage"
            )
            temp_file.write(image_download_response.content)
            temp_file.close()
            saved_file_path = temp_file.name
        
        print(f"Image saved to: {saved_file_path}")
        return {"image": saved_file_path}
            
    except requests.exceptions.Timeout:
        raise Exception("API request timeout - please check network connection")
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response from API")
    except Exception as e:
        raise Exception(f"Processing error: {str(e)}")