import openai
import threading
from typing import Callable, Optional, List, Dict, Any

class OpenAIClient:
    def __init__(self, config):
        self.config = config
        self.conversation_history: List[Dict[str, str]] = []
        self.current_request_thread: Optional[threading.Thread] = None
        self.terminate_request: bool = False
        self.update_config()
    
    def update_config(self):
        """Update OpenAI configuration"""
        api_key = self.config.get_api_key()
        base_url = self.config.get_base_url()
        if api_key:
            openai.api_key = api_key
            openai.base_url = base_url
    
    def update_api_key(self, api_key: str):
        """Update API key and reinitialize client"""
        self.config.set_api_key(api_key)
        self.update_config()
    
    def update_base_url(self, base_url: str):
        """Update base URL and reinitialize client"""
        self.config.set_base_url(base_url)
        self.update_config()
    
    def update_model(self, model: str):
        """Update model"""
        self.config.set_model(model)
    
    def _parse_stop_sequences(self, stop_str: str):
        """Parse stop sequences from config string"""
        if not stop_str or not stop_str.strip():
            return None
        
        # Split by comma and clean up whitespace
        sequences = [seq.strip() for seq in stop_str.split(',') if seq.strip()]
        return sequences if sequences else None
    
    def clear_conversation(self):
        """Clear conversation history for new chat"""
        self.conversation_history = []
        self.terminate_current_request()
    
    def terminate_current_request(self):
        """Terminate current API request"""
        self.terminate_request = True
        # Fixed: can't actually kill the thread, but we set the flag
        # The thread will check this flag and exit gracefully
    
    def send_message_async(self, message: str, callback: Callable[[str], None], error_callback: Callable[[str], None]):
        """Send message to OpenAI API asynchronously"""
        # Terminate any existing request
        self.terminate_current_request()
        self.terminate_request = False
        
        def api_call():
            try:
                if not openai.api_key:
                    error_callback("API key not configured. Right-click to set your OpenAI API key.")
                    return
                
                # Check if request was terminated before starting
                if self.terminate_request:
                    error_callback("User terminated response")
                    return
                
                if not message.strip():
                    error_callback("Please enter a message.")
                    return
                
                # Add user message to conversation history
                self.conversation_history.append({"role": "user", "content": message})
                
                # Check if request was terminated before API call
                if self.terminate_request:
                    # Remove the user message we just added since request was terminated
                    self.conversation_history.pop()
                    error_callback("User terminated response")
                    return
                
                response = openai.chat.completions.create(
                    model=self.config.get_model(),
                    messages=self.conversation_history,
                    max_tokens=int(self.config.get('OpenAI', 'max_tokens', '4096')),
                    temperature=float(self.config.get('OpenAI', 'temperature', '1.0')),
                    top_p=float(self.config.get('OpenAI', 'top_p', '1.0')),
                    presence_penalty=float(self.config.get('OpenAI', 'presence_penalty', '0.0')),
                    frequency_penalty=float(self.config.get('OpenAI', 'frequency_penalty', '0.0')),
                    stop=self._parse_stop_sequences(self.config.get('OpenAI', 'stop', ''))
                )
                
                # Check if request was terminated after API call
                if self.terminate_request:
                    # Remove the user message since request was terminated
                    self.conversation_history.pop()
                    return
                
                if response.choices:
                    ai_response = response.choices[0].message.content.strip()
                    # Add AI response to conversation history
                    self.conversation_history.append({"role": "assistant", "content": ai_response})
                    callback(ai_response)
                else:
                    error_callback("No response received from API.")
                    
            except openai.AuthenticationError:
                error_callback("Invalid API key. Please check your OpenAI API key.")
            except openai.RateLimitError:
                error_callback("Rate limit exceeded. Please try again later.")
            except Exception as e:
                if "timeout" in str(e).lower():
                  error_callback("API timeout. Please try again.")
                else:
                  error_callback(f"Error: {str(e)}")
        
        # Run API call in separate thread
        self.current_request_thread = threading.Thread(target=api_call)
        self.current_request_thread.daemon = True
        self.current_request_thread.start()