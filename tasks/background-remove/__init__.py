# region generated meta
import typing
class Inputs(typing.TypedDict):
    file: str
    output_file: str

class Outputs(typing.TypedDict):
    image: str
# endregion

import os
import requests
import json
from oocana import Context
import tempfile


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
    
    file_path = params["file"]
    
    # Validate input file exists
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Construct the API endpoint URL
    url = console_api_url + "/api/tasks/fal/images/background-remove"
    
    try:
        # Prepare multipart/form-data request
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f)
            }
            
            headers = {
                'Authorization': f"Bearer {api_key}",
            }
            
            # Send POST request to background remove endpoint
            response = requests.post(url, files=files, headers=headers, timeout=120)
            response.raise_for_status()
            
            # Parse JSON response
            result_data = response.json()
            
            # Validate response structure
            if 'data' not in result_data or 'image' not in result_data['data']:
                raise ValueError("Invalid API response format: missing 'data.images'")
            
            image = result_data['data']['image']
            if not isinstance(image, dict) or 'url' not in image:
                raise ValueError("Invalid API response format: image should be an object with 'url' field")
            
            # Extract image URL
            image_url = image['url']
            if not isinstance(image_url, str) or not image_url.startswith('http'):
                raise ValueError(f"Invalid image URL: {image_url}")
            
            # Download the processed image
            try:
                image_response = requests.get(image_url, timeout=60)
                image_response.raise_for_status()
                
                print(f"Successfully retrieved image from: {image_url}")
                
                # Check if output_file parameter is provided
                output_file_path = params.get("output_file")
                
                if output_file_path:
                    # Use provided output file path
                    os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                    with open(output_file_path, 'wb') as f:
                        f.write(image_response.content)
                    saved_file_path = output_file_path
                else:
                    # Use temporary file logic as fallback
                    file_extension = os.path.splitext(image_url)[1] or '.png'
                    temp_file = tempfile.NamedTemporaryFile(
                        suffix=file_extension, 
                        delete=False,
                        dir="/oomol-driver/oomol-storage"
                    )
                    temp_file.write(image_response.content)
                    temp_file.close()
                    saved_file_path = temp_file.name
                
                # Preview the downloaded image
                context.preview({
                    "type": "image",
                    "data": saved_file_path
                })
                
                return {"image": saved_file_path}
                
            except requests.exceptions.Timeout:
                raise Exception("Image download timeout - please check network connection")
            except requests.exceptions.RequestException as e:
                raise Exception(f"Failed to download image: {str(e)}")
            
    except requests.exceptions.Timeout:
        raise Exception("API request timeout - please check network connection")
    except requests.exceptions.RequestException as e:
        raise Exception(f"API request failed: {str(e)}")
    except json.JSONDecodeError:
        raise Exception("Invalid JSON response from API")
    except Exception as e:
        raise Exception(f"Processing error: {str(e)}")