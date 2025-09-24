import configparser
import os
from pathlib import Path

class Config:
    def __init__(self):
        self.config_dir = Path.home() / '.ghostpad'
        self.config_file = self.config_dir / 'config.ini'
        self.config = configparser.ConfigParser()
        self.ensure_config_exists()
        self.load_config()
    
    def ensure_config_exists(self):
        """Create config directory and file if they don't exist"""
        self.config_dir.mkdir(exist_ok=True)
        if not self.config_file.exists():
            self.create_default_config()
    
    def create_default_config(self): #Create default configuration
        self.config['OpenAI'] = {
            'api_key': '',
            'base_url': 'https://api.openai.com/v1/',
            'model': 'gpt-3.5-turbo',
            'max_tokens': '4096',
            'temperature': '1.0',
            'top_p': '1.0',
            'presence_penalty': '0.0',
            'frequency_penalty': '0.0',
            'stop': ''
        }
        self.config['Window'] = {
            'width': '400',
            'height': '200',
            'x': '100',
            'y': '100'
        }
        self.config['Hotkey'] = {
            'toggle_keys': 'esc',
            'toggle_enabled': 'true',
            'send_keys': 'ctrl+enter',
            'send_enabled': 'true',
            'terminate_keys': 'ctrl+alt',
            'terminate_enabled': 'true',
            'exit_keys': 'ctrl+alt+backspace',
            'exit_enabled': 'true'
        }
        self.save_config()
    
    def load_config(self):
        """Load configuration from file"""
        self.config.read(self.config_file)
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as configfile:
            self.config.write(configfile)
    
    def get(self, section, key, fallback=None):
        """Get configuration value"""
        return self.config.get(section, key, fallback=fallback)
    
    def set(self, section, key, value):
        """Set configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = str(value)
        self.save_config()
    
    def get_api_key(self):
        """Get OpenAI API key"""
        return self.get('OpenAI', 'api_key', '')
    
    def set_api_key(self, api_key):
        """Set OpenAI API key"""
        self.set('OpenAI', 'api_key', api_key)
    
    def get_base_url(self):
        """Get OpenAI base URL"""
        return self.get('OpenAI', 'base_url', 'https://api.openai.com/v1/')
    
    def set_base_url(self, base_url):
        """Set OpenAI base URL"""
        self.set('OpenAI', 'base_url', base_url)
    
    def get_model(self):
        """Get OpenAI model"""
        return self.get('OpenAI', 'model', 'gpt-3.5-turbo')
    
    def set_model(self, model):
        """Set OpenAI model"""
        self.set('OpenAI', 'model', model)
    
    def get_window_geometry(self):
        """Get window geometry"""
        width = self.get('Window', 'width', '400')
        height = self.get('Window', 'height', '200')
        x = self.get('Window', 'x', '100')
        y = self.get('Window', 'y', '100')
        return int(width), int(height), int(x), int(y)
    
    def save_window_geometry(self, width, height, x, y):
        """Save window geometry"""
        self.set('Window', 'width', width)
        self.set('Window', 'height', height)
        self.set('Window', 'x', x)
        self.set('Window', 'y', y)
    
    def get_toggle_hotkey(self):
        """Get toggle hotkey combination"""
        return self.get('Hotkey', 'toggle_keys', 'esc')
    
    def set_toggle_hotkey(self, keys):
        """Set toggle hotkey combination"""
        self.set('Hotkey', 'toggle_keys', keys)
    
    def is_toggle_hotkey_enabled(self):
        """Check if toggle hotkey is enabled"""
        return self.get('Hotkey', 'toggle_enabled', 'true').lower() == 'true'
    
    def set_toggle_hotkey_enabled(self, enabled):
        """Set toggle hotkey enabled state"""
        self.set('Hotkey', 'toggle_enabled', str(enabled).lower())
    
    def get_send_hotkey(self):
        """Get send hotkey combination"""
        return self.get('Hotkey', 'send_keys', 'ctrl+enter')
    
    def set_send_hotkey(self, keys):
        """Set send hotkey combination"""
        self.set('Hotkey', 'send_keys', keys)
    
    def is_send_hotkey_enabled(self):
        """Check if send hotkey is enabled"""
        return self.get('Hotkey', 'send_enabled', 'true').lower() == 'true'
    
    def set_send_hotkey_enabled(self, enabled):
        """Set send hotkey enabled state"""
        self.set('Hotkey', 'send_enabled', str(enabled).lower())
    
    def get_terminate_hotkey(self):
        """Get terminate hotkey combination"""
        return self.get('Hotkey', 'terminate_keys', 'ctrl+alt')
    
    def set_terminate_hotkey(self, keys):
        """Set terminate hotkey combination"""
        self.set('Hotkey', 'terminate_keys', keys)
    
    def is_terminate_hotkey_enabled(self):
        """Check if terminate hotkey is enabled"""
        return self.get('Hotkey', 'terminate_enabled', 'true').lower() == 'true'
    
    def set_terminate_hotkey_enabled(self, enabled):
        """Set terminate hotkey enabled state"""
        self.set('Hotkey', 'terminate_enabled', str(enabled).lower())
    
    def get_exit_hotkey(self):
        """Get exit hotkey combination"""
        return self.get('Hotkey', 'exit_keys', 'ctrl+backspace')
    
    def set_exit_hotkey(self, keys):
        """Set exit hotkey combination"""
        self.set('Hotkey', 'exit_keys', keys)
    
    def is_exit_hotkey_enabled(self):
        """Check if exit hotkey is enabled"""
        return self.get('Hotkey', 'exit_enabled', 'true').lower() == 'true'
    
    def set_exit_hotkey_enabled(self, enabled):
        """Set exit hotkey enabled state"""
        self.set('Hotkey', 'exit_enabled', str(enabled).lower())