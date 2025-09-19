import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import time
import sys
import os
from pynput import keyboard
from pynput.keyboard import Key, KeyCode

from config import Config
from api_client import OpenAIClient

def resource_path(rel_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, rel_path)
    return os.path.join(os.path.abspath("."), rel_path)

class GhostPad:
    def __init__(self):
        self.root = tk.Tk()
        self.config = Config()
        self.api_client = OpenAIClient(self.config)
        
        # Window properties
        self.is_dragging = False
        self.is_resizing = False
        self.drag_start_x = 0
        self.drag_start_y = 0
        self.initial_click_x = 0
        self.initial_click_y = 0
        self.resize_mode = None
        self.long_press_timer = None
        self.long_press_active = False
        
        # Text state
        self.is_waiting = False
        self.original_text = ""
        self.loading_frame = None
        self.loading_squares = []
        
        # Chat history
        self.chat_history = []
        
        # Hotkey state
        self.is_hidden = False
        self.hotkey_listener = None
        self.pressed_keys = set()
        
        # Hotkey combinations
        self.toggle_hotkey_combo = set()
        self.send_hotkey_combo = set()
        self.terminate_hotkey_combo = set()
        
        self.setup_window()
        self.create_widgets()
        self.bind_events()
        self.setup_hotkey()
    
    def setup_window(self):
        """Configure the main window"""
        self.root.title("GhostPad")
        
        # Remove window decorations
        self.root.overrideredirect(True)
        
        # Set window geometry
        width, height, x, y = self.config.get_window_geometry()
        self.root.geometry(f"{width}x{height}+{x}+{y}")
        
        # Always on top
        self.root.attributes('-topmost', True)
        
        # Windows-specific settings
        if sys.platform == "win32":
            try:
                self.root.attributes('-toolwindow', True)  # Hide from taskbar
            except:
                pass
        
        # White background
        self.root.configure(bg='white')
    
    def create_widgets(self):
        """Create the text widget"""
        self.text_widget = tk.Text(
            self.root,
            bg='white',
            fg='black',
            font=('Arial', 10),
            relief='flat',
            borderwidth=0,
            highlightthickness=0,
            wrap=tk.WORD,
            padx=8,
            pady=8
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        
        # Create loading indicator (initially hidden)
        self.loading_frame = tk.Frame(
            self.root,
            bg='white'
        )
        self.loading_frame.place(relx=1.0, rely=1.0, anchor='se', x=-5, y=-5)
        
        # Create three loading squares
        self.loading_squares = []
        for i in range(3):
            square = tk.Label(
                self.loading_frame,
                text="■",
                bg='white',
                fg='lightgray',
                font=('Arial', 6),
                width=1,
                height=1
            )
            square.pack(side=tk.LEFT)
            self.loading_squares.append(square)
        
        self.loading_frame.place_forget()  # Hide initially
        
        # Focus on the text widget
        self.text_widget.focus_set()
    
    def bind_events(self):
        """Bind all event handlers"""
        # Text widget events
        self.text_widget.bind('<KeyRelease>', self.on_text_change)
        self.text_widget.bind('<Button-3>', self.show_context_menu)  # Right-click
        
        # Window border events for dragging/resizing
        self.root.bind('<B1-Motion>', self.on_mouse_drag)
        self.root.bind('<ButtonRelease-1>', self.on_mouse_release)
        
        # Text widget border events
        self.text_widget.bind('<Button-1>', self.on_text_click)
        self.text_widget.bind('<ButtonRelease-1>', self.on_text_release)
        self.text_widget.bind('<Motion>', self.on_text_motion)
        
        # Window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_hotkey(self):
        """Setup global hotkey listener"""
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        
        # Parse all hotkey combinations
        if self.config.is_toggle_hotkey_enabled():
            self.toggle_hotkey_combo = self.parse_hotkey(self.config.get_toggle_hotkey())
        else:
            self.toggle_hotkey_combo = set()
            
        if self.config.is_send_hotkey_enabled():
            self.send_hotkey_combo = self.parse_hotkey(self.config.get_send_hotkey())
        else:
            self.send_hotkey_combo = set()
            
        if self.config.is_terminate_hotkey_enabled():
            self.terminate_hotkey_combo = self.parse_hotkey(self.config.get_terminate_hotkey())
        else:
            self.terminate_hotkey_combo = set()
        
        # Start listener if any hotkeys are enabled
        if (self.config.is_toggle_hotkey_enabled() or 
            self.config.is_send_hotkey_enabled() or 
            self.config.is_terminate_hotkey_enabled()):
            self.hotkey_listener = keyboard.Listener(
                on_press=self.on_hotkey_press,
                on_release=self.on_hotkey_release
            )
            self.hotkey_listener.start()
    
    def parse_hotkey(self, hotkey_str):
        """Parse hotkey string into set of keys"""
        keys = set()
        parts = [part.strip().lower() for part in hotkey_str.split('+')]
        
        for part in parts:
            if part == 'ctrl':
                keys.add(Key.ctrl_l)
                keys.add(Key.ctrl_r)
            elif part == 'alt':
                keys.add(Key.alt_l)
                keys.add(Key.alt_r)
            elif part == 'shift':
                keys.add(Key.shift_l)
                keys.add(Key.shift_r)
            elif part == 'esc':
                keys.add(Key.esc)
            elif part == 'space':
                keys.add(Key.space)
            elif part == 'enter':
                keys.add(Key.enter)
            elif part == 'tab':
                keys.add(Key.tab)
            elif len(part) == 1:
                keys.add(KeyCode.from_char(part))
            elif part == 'x':
                keys.add(KeyCode.from_char('x'))
            elif part == 'h':
                keys.add(KeyCode.from_char('h'))
            elif part == 'g':
                keys.add(KeyCode.from_char('g'))
        
        return keys
    
    def on_hotkey_press(self, key):
        """Handle hotkey press"""
        try:
            self.pressed_keys.add(key)
            
            # Check toggle hotkey
            if self.toggle_hotkey_combo and self.check_hotkey_match(self.toggle_hotkey_combo):
                self.root.after(0, self.toggle_window)
            
            # Check send hotkey
            if self.send_hotkey_combo and self.check_hotkey_match(self.send_hotkey_combo):
                self.root.after(0, self.send_message_via_hotkey)
            
            # Check terminate hotkey (only when waiting for response)
            if (self.terminate_hotkey_combo and 
                self.check_hotkey_match(self.terminate_hotkey_combo) and 
                self.is_waiting):
                self.root.after(0, self.terminate_current_request)
                
        except Exception as e:
            pass  # Ignore hotkey errors
    
    def check_hotkey_match(self, target_keys):
        """Check if current pressed keys match target hotkey combination"""
        if not target_keys:
            return False
            
        # For single key hotkeys, check direct match
        if len(target_keys) == 1:
            return any(key in self.pressed_keys for key in target_keys)
        
        # For combination hotkeys, check if all required keys are pressed
        # Account for left/right variants of modifier keys
        required_modifiers = 0
        pressed_modifiers = 0
        
        # Count required and pressed modifier keys
        for target_key in target_keys:
            if target_key in [Key.ctrl_l, Key.ctrl_r]:
                required_modifiers += 1
                if Key.ctrl_l in self.pressed_keys or Key.ctrl_r in self.pressed_keys:
                    pressed_modifiers += 1
            elif target_key in [Key.alt_l, Key.alt_r]:
                required_modifiers += 1
                if Key.alt_l in self.pressed_keys or Key.alt_r in self.pressed_keys:
                    pressed_modifiers += 1
            elif target_key in [Key.shift_l, Key.shift_r]:
                required_modifiers += 1
                if Key.shift_l in self.pressed_keys or Key.shift_r in self.pressed_keys:
                    pressed_modifiers += 1
            else:
                # Regular key - check direct match
                if target_key not in self.pressed_keys:
                    return False
        
        # All modifiers must be pressed
        return pressed_modifiers >= required_modifiers
    
    def on_hotkey_release(self, key):
        """Handle hotkey release"""
        try:
            self.pressed_keys.discard(key)
        except Exception as e:
            pass  # Ignore hotkey errors
    
    def toggle_window(self):
        """Toggle window visibility"""
        if self.is_hidden:
            self.show_window()
        else:
            self.hide_window()
    
    def send_message_via_hotkey(self):
        """Send message via hotkey"""
        if not self.is_waiting:
            text_content = self.text_widget.get(1.0, tk.END).strip()
            if text_content:
                self.original_text = text_content
                self.send_to_api(text_content)
    
    def terminate_current_request(self):
        """Terminate current API request"""
        if self.is_waiting:
            # Set termination flag
            self.api_client.terminate_current_request()
            
            # Immediately handle termination
            self.root.after(0, self._handle_termination)
    
    def start_long_press_timer(self, x, y):
        """Start long press timer"""
        if self.long_press_timer:
            self.root.after_cancel(self.long_press_timer)
        
        self.initial_click_x = x
        self.initial_click_y = y
        self.long_press_timer = self.root.after(350, lambda: self.activate_long_press(x, y))
    
    def activate_long_press(self, x, y):
        """Activate long press mode"""
        self.long_press_active = True
        if self.resize_mode:
            self.is_resizing = True
        else:
            self.is_dragging = True
        self.root.configure(cursor='fleur')  # Change cursor to indicate drag mode
    
    def cancel_long_press_timer(self):
        """Cancel long press timer"""
        if self.long_press_timer:
            self.root.after_cancel(self.long_press_timer)
            self.long_press_timer = None
        self.long_press_active = False
        self.initial_click_x = 0
        self.initial_click_y = 0
        self.root.configure(cursor='')
    
    def on_text_motion(self, event):
        """Handle mouse motion on text widget"""
        if self.long_press_active or self.is_dragging or self.is_resizing:
            return
            
        # Get position relative to text widget
        x, y = event.x, event.y
        width = self.text_widget.winfo_width()
        height = self.text_widget.winfo_height()
        border_threshold = 12
        
        # Check if we're near a corner (for resizing)
        if ((x < border_threshold and y < border_threshold) or 
            (x > width - border_threshold and y < border_threshold) or
            (x < border_threshold and y > height - border_threshold) or
            (x > width - border_threshold and y > height - border_threshold)):
            # Show resize cursor
            if x < border_threshold and y < border_threshold:
                self.root.configure(cursor='top_left_corner')
            elif x > width - border_threshold and y < border_threshold:
                self.root.configure(cursor='top_right_corner')
            elif x < border_threshold and y > height - border_threshold:
                self.root.configure(cursor='bottom_left_corner')
            elif x > width - border_threshold and y > height - border_threshold:
                self.root.configure(cursor='bottom_right_corner')
        elif x < border_threshold or x > width - border_threshold or y < border_threshold or y > height - border_threshold:
            # Near edges but not corners - show move cursor
            self.root.configure(cursor='fleur')
        else:
            self.root.configure(cursor='')
    
    def on_mouse_drag(self, event):
        """Handle mouse drag on window (for moving/resizing)"""
        # Check if we should cancel long-press due to movement
        if self.long_press_timer and not self.long_press_active:
            dx = abs(event.x_root - self.drag_start_x)
            dy = abs(event.y_root - self.drag_start_y)
            if dx > 20 or dy > 20:
                self.cancel_long_press_timer()
                return
        
        if not self.long_press_active:
            return
        
        dx = event.x_root - self.drag_start_x
        dy = event.y_root - self.drag_start_y
        
        if self.resize_mode:
            # Resizing
            self.handle_resize(dx, dy)
        else:
            # Moving
            x = self.root.winfo_x() + dx
            y = self.root.winfo_y() + dy
            self.root.geometry(f"+{x}+{y}")
        
        self.drag_start_x = event.x_root
        self.drag_start_y = event.y_root
    
    def on_mouse_release(self, event):
        """Handle mouse release"""
        self.cancel_long_press_timer()
        self.resize_mode = None
        self.is_dragging = False
        self.is_resizing = False
        
        # Save window position
        self.save_window_geometry()
    
    def on_text_click(self, event):
        """Handle click on text widget"""
        # Get position relative to text widget
        x, y = event.x, event.y
        width = self.text_widget.winfo_width()
        height = self.text_widget.winfo_height()
        border_threshold = 12
        
        # If click is in central area (not near borders), allow normal text selection
        if (x >= border_threshold and x <= width - border_threshold and 
            y >= border_threshold and y <= height - border_threshold):
            # Cancel any existing long press and let text widget handle the click
            self.cancel_long_press_timer()
            self.text_widget.focus_set()
            return
        
        # Get position relative to text widget
        x, y = event.x, event.y
        width = self.text_widget.winfo_width()
        height = self.text_widget.winfo_height()
        border_threshold = 12
        
        # Check if we're near a corner for resizing
        cursor, resize_mode = None, None
        if x < border_threshold and y < border_threshold:
            cursor, resize_mode = 'top_left_corner', 'nw'
        elif x > width - border_threshold and y < border_threshold:
            cursor, resize_mode = 'top_right_corner', 'ne'
        elif x < border_threshold and y > height - border_threshold:
            cursor, resize_mode = 'bottom_left_corner', 'sw'
        elif x > width - border_threshold and y > height - border_threshold:
            cursor, resize_mode = 'bottom_right_corner', 'se'
        elif x < border_threshold or x > width - border_threshold or y < border_threshold or y > height - border_threshold:
            # Near edges but not corners - dragging
            cursor, resize_mode = 'fleur', None
        
        if cursor:
            # Near corner or edge - start long press
            self.start_long_press_timer(x, y)
            self.resize_mode = resize_mode
            self.drag_start_x = event.x_root
            self.drag_start_y = event.y_root
        else:
            # In center - cancel any long press and focus on text
            self.cancel_long_press_timer()
            self.text_widget.focus_set()
    
    def on_text_release(self, event):
        """Handle release on text widget"""
        self.cancel_long_press_timer()
        self.is_dragging = False
        self.is_resizing = False
        self.save_window_geometry()
    
    def handle_resize(self, dx, dy):
        """Handle window resizing"""
        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        current_x = self.root.winfo_x()
        current_y = self.root.winfo_y()
        
        new_width = current_width
        new_height = current_height
        new_x = current_x
        new_y = current_y
        
        # Handle corner resizing
        if self.resize_mode == 'se':
            new_width = max(200, current_width + dx)
            new_height = max(100, current_height + dy)
        elif self.resize_mode == 'sw':
            new_width = max(200, current_width - dx)
            new_height = max(100, current_height + dy)
            if new_width > 200:
                new_x = current_x + dx
        elif self.resize_mode == 'ne':
            new_width = max(200, current_width + dx)
            new_height = max(100, current_height - dy)
            if new_height > 100:
                new_y = current_y + dy
        elif self.resize_mode == 'nw':
            new_width = max(200, current_width - dx)
            new_height = max(100, current_height - dy)
            if new_width > 200:
                new_x = current_x + dx
            if new_height > 100:
                new_y = current_y + dy
        
        self.root.geometry(f"{new_width}x{new_height}+{new_x}+{new_y}")
    
    def on_text_change(self, event):
        """Handle text change - only handle normal Enter now"""
        if event.keysym == 'Return':
            # Normal Enter - just insert newline (default behavior)
            return None
    
    def send_to_api(self, message):
        """Send message to OpenAI API"""
        if self.is_waiting:
            return
        
        self.is_waiting = True
        
        # Add user message to chat history
        self.chat_history.append(("User", message))
        
        # Show loading indicator (keep text in place)
        self.loading_frame.place(relx=1.0, rely=1.0, anchor='se', x=-5, y=-5)
        
        # Send to API
        self.api_client.send_message_async(
            message,
            self.on_api_response,
            self.on_api_error
        )
    
    def on_api_response(self, response):
        """Handle API response"""
        self.root.after(0, lambda: self._update_text_with_response(response))
    
    def on_api_error(self, error):
        """Handle API error"""
        self.root.after(0, lambda: self._update_text_with_error(error))
    
    def _update_text_with_response(self, response):
        """Update text widget with API response"""
        # Hide loading indicator
        self.loading_frame.place_forget()
        
        # Add AI response to chat history
        self.chat_history.append(("AI", response))
        
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(1.0, response)
        self.text_widget.configure(fg='black')
        self.is_waiting = False
    
    def _update_text_with_error(self, error):
        """Update text widget with error message"""
        # Hide loading indicator
        self.loading_frame.place_forget()
        
        # Add error to chat history
        self.chat_history.append(("Error", error))
        
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(1.0, error)
        self.text_widget.configure(fg='red')
        self.is_waiting = False
        
        # After 3 seconds, restore original text or show placeholder
        self.root.after(3000, self._restore_text_after_error)
    
    def _restore_text_after_error(self):
        """Restore text after showing error"""
        if self.original_text:
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, self.original_text)
            self.text_widget.configure(fg='black')
    
    def _handle_termination(self):
        """Handle immediate termination response"""
        if self.is_waiting:
            # Hide loading indicator
            self.loading_frame.place_forget()
            
            # Add termination to chat history
            self.chat_history.append(("System", "Successfully terminated"))
            
            # Update text widget
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(1.0, "Successfully terminated")
            self.text_widget.configure(fg='orange')
            
            # Reset waiting state
            self.is_waiting = False
            
            # After 2 seconds, restore original text or clear
            self.root.after(2000, self._restore_text_after_termination)
    
    def _restore_text_after_termination(self):
        """Restore text after showing termination message"""
        if not self.is_waiting:  # Only restore if not waiting for new response
            self.text_widget.delete(1.0, tk.END)
            if self.original_text:
                self.text_widget.insert(1.0, self.original_text)
            self.text_widget.configure(fg='black')
    
    def show_context_menu(self, event):
        """Show right-click context menu"""
        context_menu = tk.Menu(self.root, tearoff=0)
        
        context_menu.add_command(label="LLM Settings", command=self.show_llm_settings)
        context_menu.add_command(label="Set Hotkeys", command=self.set_hotkeys)
        context_menu.add_separator()
        context_menu.add_command(label="Start New Chat", command=self.start_new_chat)
        context_menu.add_command(label="History", command=self.show_history)
        context_menu.add_separator()
        context_menu.add_command(label="Help", command=self.show_help)
        context_menu.add_separator()
        context_menu.add_command(label="Hide", command=self.hide_window)
        context_menu.add_command(label="Exit", command=self.on_closing)
        
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def show_llm_settings(self):
        """Show LLM settings window"""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x600")
        settings_window.configure(bg='white')
        settings_window.attributes('-topmost', True)
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Center the window
        settings_window.update_idletasks()
        x = (settings_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (settings_window.winfo_screenheight() // 2) - (600 // 2)
        settings_window.geometry(f"500x600+{x}+{y}")
        
        # Create main container frame
        container = tk.Frame(settings_window, bg='white')
        container.pack(fill=tk.BOTH, expand=True)
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(container, bg='white', highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg='white')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Main frame (now inside scrollable_frame)
        main_frame = tk.Frame(scrollable_frame, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="LLM Settings", font=('Arial', 14, 'bold'), bg='white')
        title_label.pack(pady=(0, 20))
        
        # API Key section
        api_frame = tk.Frame(main_frame, bg='white')
        api_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(api_frame, text="API Key:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_key = self.config.get_api_key()
        masked_key = f"{'*' * max(0, len(current_key) - 4)}{current_key[-4:]}" if current_key else "Not set"
        tk.Label(api_frame, text=f"Current: {masked_key}", font=('Arial', 9), bg='white', fg='gray').pack(anchor='w')
        
        api_entry = tk.Entry(api_frame, font=('Arial', 10), show='*', width=50)
        api_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Base URL section
        url_frame = tk.Frame(main_frame, bg='white')
        url_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(url_frame, text="Base URL:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_url = self.config.get_base_url()
        tk.Label(url_frame, text=f"Current: {current_url}", font=('Arial', 9), bg='white', fg='gray').pack(anchor='w')
        
        url_entry = tk.Entry(url_frame, font=('Arial', 10), width=50)
        url_entry.pack(fill=tk.X, pady=(5, 0))
        url_entry.insert(0, current_url)
        
        # Model section
        model_frame = tk.Frame(main_frame, bg='white')
        model_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(model_frame, text="Model:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_model = self.config.get_model()
        tk.Label(model_frame, text=f"Current: {current_model}", font=('Arial', 9), bg='white', fg='gray').pack(anchor='w')
        tk.Label(model_frame, text="Examples: gpt-4.1-mini, gpt-3.5-turbo, gpt-4", font=('Arial', 8), bg='white', fg='lightgray').pack(anchor='w')
        
        model_entry = tk.Entry(model_frame, font=('Arial', 10), width=50)
        model_entry.pack(fill=tk.X, pady=(5, 0))
        model_entry.insert(0, current_model)
        
        # Advanced Settings Section
        advanced_label = tk.Label(main_frame, text="Advanced Settings", font=('Arial', 12, 'bold'), bg='white')
        advanced_label.pack(pady=(20, 10))
        
        # Temperature
        temp_frame = tk.Frame(main_frame, bg='white')
        temp_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(temp_frame, text="Temperature:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_temp = self.config.get('OpenAI', 'temperature', '1.0')
        tk.Label(temp_frame, text=f"Current: {current_temp} | Controls randomness", font=('Arial', 8), bg='white', fg='gray').pack(anchor='w')
        
        temp_entry = tk.Entry(temp_frame, font=('Arial', 10), width=20)
        temp_entry.pack(anchor='w', pady=(2, 0))
        temp_entry.insert(0, current_temp)
        
        # Top P
        top_p_frame = tk.Frame(main_frame, bg='white')
        top_p_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(top_p_frame, text="Top P:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_top_p = self.config.get('OpenAI', 'top_p', '1.0')
        tk.Label(top_p_frame, text=f"Current: {current_top_p} | Limits randomness range", font=('Arial', 8), bg='white', fg='gray').pack(anchor='w')
        
        top_p_entry = tk.Entry(top_p_frame, font=('Arial', 10), width=20)
        top_p_entry.pack(anchor='w', pady=(2, 0))
        top_p_entry.insert(0, current_top_p)
        
        # Max Tokens
        max_tokens_frame = tk.Frame(main_frame, bg='white')
        max_tokens_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(max_tokens_frame, text="Max Tokens:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_max_tokens = self.config.get('OpenAI', 'max_tokens', '4096')
        tk.Label(max_tokens_frame, text=f"Current: {current_max_tokens} | Maximum response length", font=('Arial', 8), bg='white', fg='gray').pack(anchor='w')
        
        max_tokens_entry = tk.Entry(max_tokens_frame, font=('Arial', 10), width=20)
        max_tokens_entry.pack(anchor='w', pady=(2, 0))
        max_tokens_entry.insert(0, current_max_tokens)
        
        # Presence Penalty
        presence_frame = tk.Frame(main_frame, bg='white')
        presence_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(presence_frame, text="Presence Penalty:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_presence = self.config.get('OpenAI', 'presence_penalty', '0.0')
        tk.Label(presence_frame, text=f"Current: {current_presence} | Encourages new topics (positive values)", font=('Arial', 8), bg='white', fg='gray').pack(anchor='w')
        
        presence_entry = tk.Entry(presence_frame, font=('Arial', 10), width=20)
        presence_entry.pack(anchor='w', pady=(2, 0))
        presence_entry.insert(0, current_presence)
        
        # Frequency Penalty
        frequency_frame = tk.Frame(main_frame, bg='white')
        frequency_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(frequency_frame, text="Frequency Penalty:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_frequency = self.config.get('OpenAI', 'frequency_penalty', '0.0')
        tk.Label(frequency_frame, text=f"Current: {current_frequency} | Reduces repetition (positive values)", font=('Arial', 8), bg='white', fg='gray').pack(anchor='w')
        
        frequency_entry = tk.Entry(frequency_frame, font=('Arial', 10), width=20)
        frequency_entry.pack(anchor='w', pady=(2, 0))
        frequency_entry.insert(0, current_frequency)
        
        # Stop Sequences
        stop_frame = tk.Frame(main_frame, bg='white')
        stop_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(stop_frame, text="Stop Sequences:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_stop = self.config.get('OpenAI', 'stop', '')
        tk.Label(stop_frame, text=f"Current: {current_stop if current_stop else 'None'} | Comma-separated stop words", font=('Arial', 8), bg='white', fg='gray').pack(anchor='w')
        
        stop_entry = tk.Entry(stop_frame, font=('Arial', 10), width=50)
        stop_entry.pack(fill=tk.X, pady=(2, 0))
        stop_entry.insert(0, current_stop)
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_settings():
            # Save API key if provided
            api_key = api_entry.get().strip()
            if api_key:
                self.api_client.update_api_key(api_key)
            
            # Save base URL
            base_url = url_entry.get().strip()
            if base_url:
                if not base_url.endswith('/v1/'):
                    if not base_url.endswith('/'):
                        base_url += '/'
                    base_url += 'v1/'
                self.api_client.update_base_url(base_url)
            
            # Save model
            model = model_entry.get().strip()
            if model:
                self.api_client.update_model(model)
            
            # Save advanced settings
            try:
                temp = float(temp_entry.get().strip())
                if 0.0 <= temp <= 2.0:
                    self.config.set('OpenAI', 'temperature', str(temp))
            except ValueError:
                pass
            
            try:
                top_p = float(top_p_entry.get().strip())
                if 0.0 <= top_p <= 1.0:
                    self.config.set('OpenAI', 'top_p', str(top_p))
            except ValueError:
                pass
            
            try:
                max_tokens = int(max_tokens_entry.get().strip())
                if max_tokens > 0:
                    self.config.set('OpenAI', 'max_tokens', str(max_tokens))
            except ValueError:
                pass
            
            try:
                presence = float(presence_entry.get().strip())
                if -2.0 <= presence <= 2.0:
                    self.config.set('OpenAI', 'presence_penalty', str(presence))
            except ValueError:
                pass
            
            try:
                frequency = float(frequency_entry.get().strip())
                if -2.0 <= frequency <= 2.0:
                    self.config.set('OpenAI', 'frequency_penalty', str(frequency))
            except ValueError:
                pass
            
            # Save stop sequences
            stop_sequences = stop_entry.get().strip()
            self.config.set('OpenAI', 'stop', stop_sequences)
            
            settings_window.destroy()
            messagebox.showinfo("Success", "LLM settings updated successfully!")
        
        def cancel_settings():
            settings_window.destroy()
        
        tk.Button(button_frame, text="Save", command=save_settings, bg='#4CAF50', fg='white', font=('Arial', 10), padx=20).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Button(button_frame, text="Cancel", command=cancel_settings, bg='#f44336', fg='white', font=('Arial', 10), padx=20).pack(side=tk.RIGHT)
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel to canvas
        canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))   # Linux
        
        # Make sure canvas has focus for scrolling
        canvas.focus_set()
    
    def set_hotkeys(self):
        """Show dialog to set all hotkeys"""
        hotkey_window = tk.Toplevel(self.root)
        hotkey_window.title("Hotkey Settings")
        hotkey_window.geometry("600x550")
        hotkey_window.configure(bg='white')
        hotkey_window.attributes('-topmost', True)
        hotkey_window.transient(self.root)
        hotkey_window.grab_set()
        
        # Center the window
        hotkey_window.update_idletasks()
        x = (hotkey_window.winfo_screenwidth() // 2) - (300)
        y = (hotkey_window.winfo_screenheight() // 2) - (275)
        hotkey_window.geometry(f"600x550+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(hotkey_window, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Hotkey Settings", font=('Arial', 14, 'bold'), bg='white')
        title_label.pack(pady=(0, 20))
        
        # Instructions
        instructions = tk.Label(
            main_frame,
            text="Supported keys: ctrl, alt, shift, esc, space, enter, tab, a-z, 0-9, f1-f12\n"
                 "Examples: esc, ctrl+h, alt+space, ctrl+shift+x",
            font=('Arial', 9),
            bg='white',
            fg='gray',
            justify=tk.LEFT
        )
        instructions.pack(pady=(0, 20))
        
        # Toggle hotkey section
        toggle_frame = tk.Frame(main_frame, bg='white')
        toggle_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(toggle_frame, text="Hide/Show Window:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_toggle = self.config.get_toggle_hotkey()
        tk.Label(toggle_frame, text=f"Current: {current_toggle}", font=('Arial', 9), bg='white', fg='gray').pack(anchor='w')
        
        toggle_entry = tk.Entry(toggle_frame, font=('Arial', 10), width=30)
        toggle_entry.pack(anchor='w', pady=(5, 0))
        toggle_entry.insert(0, current_toggle)
        
        toggle_enabled_var = tk.BooleanVar(value=self.config.is_toggle_hotkey_enabled())
        toggle_enabled_check = tk.Checkbutton(
            toggle_frame, 
            text="Enabled", 
            variable=toggle_enabled_var, 
            bg='white', 
            font=('Arial', 9)
        )
        toggle_enabled_check.pack(anchor='w', pady=(5, 0))
        
        # Send hotkey section
        send_frame = tk.Frame(main_frame, bg='white')
        send_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(send_frame, text="Send Message:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_send = self.config.get_send_hotkey()
        tk.Label(send_frame, text=f"Current: {current_send}", font=('Arial', 9), bg='white', fg='gray').pack(anchor='w')
        
        send_entry = tk.Entry(send_frame, font=('Arial', 10), width=30)
        send_entry.pack(anchor='w', pady=(5, 0))
        send_entry.insert(0, current_send)
        
        send_enabled_var = tk.BooleanVar(value=self.config.is_send_hotkey_enabled())
        send_enabled_check = tk.Checkbutton(
            send_frame, 
            text="Enabled", 
            variable=send_enabled_var, 
            bg='white', 
            font=('Arial', 9)
        )
        send_enabled_check.pack(anchor='w', pady=(5, 0))
        
        # Terminate hotkey section
        terminate_frame = tk.Frame(main_frame, bg='white')
        terminate_frame.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(terminate_frame, text="Force Terminate Response:", font=('Arial', 10, 'bold'), bg='white').pack(anchor='w')
        current_terminate = self.config.get_terminate_hotkey()
        tk.Label(terminate_frame, text=f"Current: {current_terminate} (only works when waiting for response)", font=('Arial', 9), bg='white', fg='gray').pack(anchor='w')
        
        terminate_entry = tk.Entry(terminate_frame, font=('Arial', 10), width=30)
        terminate_entry.pack(anchor='w', pady=(5, 0))
        terminate_entry.insert(0, current_terminate)
        
        terminate_enabled_var = tk.BooleanVar(value=self.config.is_terminate_hotkey_enabled())
        terminate_enabled_check = tk.Checkbutton(
            terminate_frame, 
            text="Enabled", 
            variable=terminate_enabled_var, 
            bg='white', 
            font=('Arial', 9)
        )
        terminate_enabled_check.pack(anchor='w', pady=(5, 0))
        
        # Buttons
        button_frame = tk.Frame(main_frame, bg='white')
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        def save_hotkeys():
            # Validate and save toggle hotkey
            toggle_hotkey = toggle_entry.get().strip().lower()
            if toggle_hotkey and self.validate_hotkey(toggle_hotkey):
                self.config.set_toggle_hotkey(toggle_hotkey)
                self.config.set_toggle_hotkey_enabled(toggle_enabled_var.get())
            elif toggle_hotkey:
                messagebox.showerror("Error", f"Invalid toggle hotkey: {toggle_hotkey}")
                return
            
            # Validate and save send hotkey
            send_hotkey = send_entry.get().strip().lower()
            if send_hotkey and self.validate_hotkey(send_hotkey):
                self.config.set_send_hotkey(send_hotkey)
                self.config.set_send_hotkey_enabled(send_enabled_var.get())
            elif send_hotkey:
                messagebox.showerror("Error", f"Invalid send hotkey: {send_hotkey}")
                return
            
            # Validate and save terminate hotkey
            terminate_hotkey = terminate_entry.get().strip().lower()
            if terminate_hotkey and self.validate_hotkey(terminate_hotkey):
                self.config.set_terminate_hotkey(terminate_hotkey)
                self.config.set_terminate_hotkey_enabled(terminate_enabled_var.get())
            elif terminate_hotkey:
                messagebox.showerror("Error", f"Invalid terminate hotkey: {terminate_hotkey}")
                return
            
            # Restart hotkey listener with new settings
            self.setup_hotkey()
            hotkey_window.destroy()
            messagebox.showinfo("Success", "Hotkeys updated successfully!")
        
        def cancel_hotkeys():
            hotkey_window.destroy()
        
        tk.Button(button_frame, text="Save", command=save_hotkeys, bg='#4CAF50', fg='white', font=('Arial', 10), padx=20).pack(side=tk.RIGHT, padx=(10, 0))
        tk.Button(button_frame, text="Cancel", command=cancel_hotkeys, bg='#f44336', fg='white', font=('Arial', 10), padx=20).pack(side=tk.RIGHT)
    
    def validate_hotkey(self, hotkey_str):
        """Validate hotkey format"""
        parts = [part.strip().lower() for part in hotkey_str.split('+')]
        if len(parts) > 3:
            return False
        
        valid_keys = ['ctrl', 'alt', 'shift', 'esc', 'space', 'enter', 'tab'] + \
                    [chr(i) for i in range(ord('a'), ord('z')+1)] + \
                    [str(i) for i in range(10)] + \
                    [f'f{i}' for i in range(1, 13)]
        
        invalid_keys = [part for part in parts if part not in valid_keys]
        return len(invalid_keys) == 0
    
    def start_new_chat(self):
        """Start a new chat session"""
        self.api_client.clear_conversation()
        self.chat_history.clear()
        self.text_widget.delete(1.0, tk.END)
        self.original_text = ""
    
    def show_history(self):
        """Show chat history window"""
        history_window = tk.Toplevel(self.root)
        history_window.title("Chat History")
        history_window.geometry("700x500")
        history_window.configure(bg='white')
        history_window.attributes('-topmost', True)
        history_window.transient(self.root)
        
        # Center the window
        history_window.update_idletasks()
        x = (history_window.winfo_screenwidth() // 2) - (700 // 2)
        y = (history_window.winfo_screenheight() // 2) - (500 // 2)
        history_window.geometry(f"700x500+{x}+{y}")
        
        # Main frame
        main_frame = tk.Frame(history_window, bg='white', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = tk.Label(main_frame, text="Chat History", font=('Arial', 14, 'bold'), bg='white')
        title_label.pack(pady=(0, 20))
        
        # Scrollable text area
        text_frame = tk.Frame(main_frame, bg='white')
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Text widget
        history_text = tk.Text(
            text_frame,
            bg='white',
            fg='black',
            font=('Arial', 10),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10,
            state=tk.DISABLED
        )
        history_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=history_text.yview)
        
        # Configure text tags for styling
        history_text.tag_configure("user", foreground="#2196F3", font=('Arial', 10, 'bold'))
        history_text.tag_configure("ai", foreground="#4CAF50", font=('Arial', 10, 'bold'))
        history_text.tag_configure("system", foreground="#FF9800", font=('Arial', 10, 'bold'))
        history_text.tag_configure("error", foreground="#f44336", font=('Arial', 10, 'bold'))
        history_text.tag_configure("content", foreground="black", font=('Arial', 10))
        
        # Populate history
        history_text.config(state=tk.NORMAL)
        if not self.chat_history:
            history_text.insert(tk.END, "None")
        else:
            for i, (sender, message) in enumerate(self.chat_history):
                if i > 0:
                    history_text.insert(tk.END, "\n" + "="*50 + "\n\n")
                
                # Add sender label
                if sender == "Error":
                    history_text.insert(tk.END, f"{sender}:\n", "error")
                elif sender == "System":
                    history_text.insert(tk.END, f"{sender}:\n", "system")
                else:
                    history_text.insert(tk.END, f"{sender}:\n", sender.lower())
                
                # Add message content
                history_text.insert(tk.END, f"{message}\n", "content")
        
        history_text.config(state=tk.DISABLED)
        
        # Close button
        close_button = tk.Button(
            main_frame,
            text="Close",
            command=history_window.destroy,
            bg='#2196F3',
            fg='white',
            font=('Arial', 10),
            padx=20
        )
        close_button.pack(pady=(20, 0))

    def show_help(self):
        """Show help window with README content"""
        help_window = tk.Toplevel(self.root)
        help_window.title("Help")
        help_window.geometry("800x600")
        help_window.configure(bg='white')
        
        # Make help window stay on top but not always
        help_window.attributes('-topmost', False)
        help_window.transient(self.root)
        
        # Create scrollable text widget
        frame = tk.Frame(help_window, bg='white')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Text widget
        text_widget = tk.Text(
            frame,
            bg='white',
            fg='black',
            font=('Arial', 10),
            wrap=tk.WORD,
            yscrollcommand=scrollbar.set,
            padx=10,
            pady=10
        )
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text_widget.yview)
        
        # Load and display README content
        try:
            with open(resource_path("README.md"), 'r', encoding='utf-8') as f:
                readme_content = f.read()
            text_widget.insert(1.0, readme_content)
        except FileNotFoundError:
            text_widget.insert(1.0, "README.md file not found.")
        except Exception as e:
            text_widget.insert(1.0, f"Error loading README.md: {str(e)}")
        
        # README widget read-only
        text_widget.config(state=tk.DISABLED)
        
        # Center help window
        help_window.update_idletasks()
        x = (help_window.winfo_screenwidth() // 2) - (800 // 2)
        y = (help_window.winfo_screenheight() // 2) - (600 // 2)
        help_window.geometry(f"800x600+{x}+{y}")
    
    def hide_window(self):
        """Hide the window"""
        if not self.is_hidden:
            self.root.withdraw()
            self.is_hidden = True
    
    def show_window(self):
        """Show the window"""
        if self.is_hidden:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes('-topmost', True)
            self.is_hidden = False
    
    def save_window_geometry(self):
        """Save current window geometry"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        
        self.config.save_window_geometry(width, height, x, y)
    
    def on_closing(self):
        """Handle window closing"""
        self.save_window_geometry()
        if self.hotkey_listener:
            self.hotkey_listener.stop()
        self.root.quit()
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = GhostPad()
    app.run()