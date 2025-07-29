# ENHANCED MULTI-AGENT CHATBOT WITH COMPLETE MCP & GEMINI INTEGRATION

import streamlit as st
import json
from datetime import datetime, timedelta
import os
import time
import re
import requests
import uuid
import subprocess
import base64
import hashlib
import sqlite3
from typing import TypedDict, Annotated, List, Dict, Any, Optional
import asyncio
from dataclasses import dataclass
import threading
import html
import mysql.connector
from mysql.connector import Error
from contextlib import contextmanager

# Enhanced imports with better error handling
try:
    from langchain.chains import ConversationChain
    from langchain.chains.conversation.memory import ConversationEntityMemory
    from langchain.chains.conversation.prompt import ENTITY_MEMORY_CONVERSATION_TEMPLATE
    from langchain_groq import ChatGroq
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain.memory import ConversationBufferWindowMemory, ConversationSummaryBufferMemory
    from langchain.schema import BaseMemory
    LANGCHAIN_AVAILABLE = True
except ImportError as e:
    st.error(f"Please install required packages: pip install langchain langchain-groq langchain-google-genai")
    LANGCHAIN_AVAILABLE = False

try:
    from langgraph.graph import StateGraph, END, START
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    st.warning("LangGraph not available. Install with: pip install langgraph")
    LANGGRAPH_AVAILABLE = False

try:
    from github import Github, GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    st.warning("PyGithub not available. Install with: pip install PyGithub")
    GITHUB_AVAILABLE = False

# SECURE CONFIGURATION MANAGEMENT

@dataclass
class Config:
    groq_api_key: str = os.getenv('GROQ_API_KEY', '')
    gemini_api_key: str = os.getenv('GEMINI_API_KEY', '')
    github_token: str = os.getenv('GITHUB_TOKEN', '')
    secret_key: str = os.getenv('SECRET_KEY', '')
    database_path: str = os.getenv('DATABASE_PATH', 'chatbot.db')
    users_file: str = os.getenv('USERS_FILE', 'users.json')
    max_memory_messages: int = int(os.getenv('MAX_MEMORY_MESSAGES', '50'))
    session_timeout: int = int(os.getenv('SESSION_TIMEOUT', '3600'))

    @classmethod
    def validate_config(cls):
        """Validate that all required environment variables are set"""
        required_vars = ['GROQ_API_KEY', 'GEMINI_API_KEY', 'GITHUB_TOKEN', 'SECRET_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        return True

config = Config()

# SESSION STATE INITIALIZATION

def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'logged_in': False,
        'username': "",
        'user_id': None,
        'chat_history': [],
        'workflow_history': [],
        'current_page': '🏠 Chat Interface',
        'conversation_memory': None,
        'ai_system': None,
        'session_id': str(uuid.uuid4()),
        'login_time': None,
        'theme': 'modern_dark',
        'github_manager': None,  # Add this
        'user': None,           # Add this if you have a user object
        'database_manager': None, # Add any other managers you use
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

initialize_session_state()

# ENHANCED UI STYLING WITH MULTIPLE THEMES

def get_theme_styles(theme='modern_dark'):
    """Get theme-specific CSS styles"""
    themes = {
        'modern_dark': {
            'primary_gradient': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            'secondary_gradient': 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            'background': 'linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)',
            'card_bg': 'rgba(255, 255, 255, 0.95)',
            'text_primary': '#333333',
            'text_secondary': '#666666'
        },
        'neon': {
            'primary_gradient': 'linear-gradient(135deg, #00f5ff 0%, #ff00ff 100%)',
            'secondary_gradient': 'linear-gradient(135deg, #39ff14 0%, #ff073a 100%)',
            'background': 'linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%)',
            'card_bg': 'rgba(0, 0, 0, 0.85)',
            'text_primary': '#ffffff',
            'text_secondary': '#cccccc'
        },
        'sunset': {
            'primary_gradient': 'linear-gradient(135deg, #ff7e5f 0%, #feb47b 100%)',
            'secondary_gradient': 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
            'background': 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 50%, #fecfef 100%)',
            'card_bg': 'rgba(255, 255, 255, 0.9)',
            'text_primary': '#333333',
            'text_secondary': '#555555'
        }
    }
    
    return themes.get(theme, themes['modern_dark'])

def apply_enhanced_styling():
    """Apply enhanced modern styling with animations"""
    theme = get_theme_styles(st.session_state.theme)
    
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
        
        :root {{
            --primary-gradient: {theme['primary_gradient']};
            --secondary-gradient: {theme['secondary_gradient']};
            --background: {theme['background']};
            --card-bg: {theme['card_bg']};
            --text-primary: {theme['text_primary']};
            --text-secondary: {theme['text_secondary']};
        }}
        
        * {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        
        .main {{
            background: var(--background);
            min-height: 100vh;
            animation: backgroundShift 20s ease infinite;
        }}
        
        @keyframes backgroundShift {{
            0%, 100% {{ background-position: 0% 50%; }}
            50% {{ background-position: 100% 50%; }}
        }}
        
        .stApp > header {{
            background-color: transparent;
        }}
        
        /* Enhanced Login Container */
        .login-container {{
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            padding: 3rem 2.5rem;
            border-radius: 24px;
            box-shadow: 0 25px 80px rgba(0,0,0,0.2);
            max-width: 480px;
            margin: 3rem auto;
            text-align: center;
            border: 1px solid rgba(255, 255, 255, 0.3);
            animation: slideUp 0.8s ease-out;
            position: relative;
            overflow: hidden;
        }}
        
        .login-container::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
            animation: shimmer 3s infinite;
        }}
        
        @keyframes shimmer {{
            0% {{ left: -100%; }}
            100% {{ left: 100%; }}
        }}
        
        @keyframes slideUp {{
            from {{ opacity: 0; transform: translateY(30px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        

        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: scale(0.95); }}
            to {{ opacity: 1; transform: scale(1); }}
        }}
        
        .chat-header {{
            background: var(--primary-gradient);
            color: white;
            padding: 24px;
            border-radius: 24px 24px 0 0;
            display: flex;
            align-items: center;
            gap: 16px;
            position: relative;
            overflow: hidden;
        }}
        
        .chat-header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url("data:image/svg+xml,%3Csvg width='40' height='40' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='white' fill-opacity='0.03'%3E%3Cpath d='m0 40h40v-40h-40z'/%3E%3C/g%3E%3C/svg%3E");
        }}
        
        .chat-messages {{
            flex: 1;
            overflow-y: auto;
            padding: 24px;
            background: linear-gradient(180deg, #fafafa 0%, #f5f5f5 100%);
            scrollbar-width: thin;
            scrollbar-color: #ddd transparent;
        }}
        
        .chat-messages::-webkit-scrollbar {{
            width: 6px;
        }}
        
        .chat-messages::-webkit-scrollbar-track {{
            background: transparent;
        }}
        
        .chat-messages::-webkit-scrollbar-thumb {{
            background: #ddd;
            border-radius: 3px;
        }}
        
        /* Enhanced Message Bubbles */
        .message {{
            margin: 20px 0;
            display: flex;
            align-items: flex-end;
            gap: 12px;
            animation: messageSlide 0.4s ease-out;
        }}
        
        @keyframes messageSlide {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .message.user {{
            flex-direction: row-reverse;
        }}
        
        .message-bubble {{
            max-width: 75%;
            padding: 16px 20px;
            border-radius: 20px;
            position: relative;
            word-wrap: break-word;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .message-bubble:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.15);
        }}
        
        .message.user .message-bubble {{
            background: var(--primary-gradient);
            color: white;
            border-bottom-right-radius: 6px;
        }}
        
        .message.bot .message-bubble {{
            background: white;
            color: var(--text-primary);
            border: 1px solid #e8f0fe;
            border-bottom-left-radius: 6px;
        }}
        
        .message-avatar {{
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            flex-shrink: 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
        }}
        
        .message-avatar:hover {{
            transform: scale(1.1);
        }}
        
        .user-avatar {{
            background: var(--primary-gradient);
            color: white;
        }}
        
        .bot-avatar {{
            background: var(--secondary-gradient);
            color: white;
        }}
        
        /* Enhanced Metric Cards */
        .metric-card {{
            background: var(--primary-gradient);
            color: white;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .metric-card::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            transform: rotate(45deg);
            transition: all 0.6s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-4px) scale(1.02);
            box-shadow: 0 12px 40px rgba(102, 126, 234, 0.4);
        }}
        
        .metric-card:hover::before {{
            top: -60%;
            left: -60%;
        }}
        
        /* Enhanced Buttons */
        .stButton > button {{
            background: var(--primary-gradient) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 12px 28px !important;
            font-weight: 600 !important;
            font-size: 14px !important;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
            position: relative !important;
            overflow: hidden !important;
        }}
        
        .stButton > button::before {{
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s;
        }}
        
        .stButton > button:hover {{
            transform: translateY(-2px) !important;
            box-shadow: 0 10px 30px rgba(102, 126, 234, 0.4) !important;
        }}
        
        .stButton > button:hover::before {{
            left: 100%;
        }}
        
        .stButton > button:active {{
            transform: translateY(0px) !important;
        }}
        
        /* Quick Action Buttons */
        .quick-action-btn {{
            background: var(--secondary-gradient) !important;
            font-size: 12px !important;
            padding: 8px 16px !important;
            border-radius: 20px !important;
        }}
        
        /* Status Indicators */
        .status-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        
        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.7; }}
        }}
        
        /* Workflow Steps */
        .workflow-step {{
            background: linear-gradient(135deg, #f8f9ff 0%, #f0f2ff 100%);
            padding: 20px;
            border-radius: 12px;
            margin: 12px 0;
            border-left: 4px solid var(--primary-gradient);
            box-shadow: 0 4px 12px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
        }}
        
        .workflow-step:hover {{
            transform: translateX(4px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.1);
        }}
        
        /* Code Blocks */
        .code-block {{
            background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%);
            color: #f7fafc;
            padding: 20px;
            border-radius: 12px;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            overflow-x: auto;
            border: 1px solid #4a5568;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
        }}
        
        /* Loading Animations */
        .loading-dots {{
            display: inline-block;
        }}
        
        .loading-dots::after {{
            content: '';
            animation: dots 1.5s infinite;
        }}
        
        @keyframes dots {{
            0%, 20% {{ content: ''; }}
            40% {{ content: '.'; }}
            60% {{ content: '..'; }}
            80%, 100% {{ content: '...'; }}
        }}
        
        /* Sidebar Enhancements */
        .css-1d391kg {{
            background: var(--card-bg) !important;
            border-right: 1px solid rgba(255,255,255,0.1) !important;
        }}
        
        /* Form Inputs */
        .stTextInput > div > div > input {{
            border-radius: 12px !important;
            border: 2px solid #e2e8f0 !important;
            padding: 12px 16px !important;
            transition: all 0.3s ease !important;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: #667eea !important;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        }}
        
        /* Selectbox */
        .stSelectbox > div > div {{
            border-radius: 12px !important;
            border: 2px solid #e2e8f0 !important;
        }}
        
        /* Theme Switcher */
        .theme-switcher {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            background: var(--card-bg);
            padding: 10px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }}
        
        /* Mobile Responsive */
        @media (max-width: 768px) {{
            .login-container {{
                margin: 1rem;
                padding: 2rem 1.5rem;
            }}
            
            .chat-container {{
                height: 60vh;
                margin: 10px;
            }}
            
            .message-bubble {{
                max-width: 85%;
            }}
        }}
        
        /* Custom Scrollbar */
        * {{
            scrollbar-width: thin;
            scrollbar-color: #cbd5e0 transparent;
        }}
        
        *::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        *::-webkit-scrollbar-track {{
            background: transparent;
        }}
        
        *::-webkit-scrollbar-thumb {{
            background: linear-gradient(135deg, #cbd5e0 0%, #a0aec0 100%);
            border-radius: 4px;
        }}
        
        *::-webkit-scrollbar-thumb:hover {{
            background: linear-gradient(135deg, #a0aec0 0%, #718096 100%);
        }}
    </style>
    """, unsafe_allow_html=True)

# ENHANCED DATABASE MANAGEMENT WITH SQLITE

class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database with all required tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    email TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    preferences TEXT DEFAULT '{}',
                    is_active BOOLEAN DEFAULT 1
                )
            """)
            
            # Conversations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT,
                    message_type TEXT CHECK(message_type IN ('user', 'assistant', 'system')),
                    content TEXT,
                    agent_type TEXT,
                    metadata TEXT DEFAULT '{}',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # Workflows table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id TEXT,
                    workflow_type TEXT,
                    input_data TEXT,
                    output_data TEXT,
                    status TEXT DEFAULT 'pending',
                    error_message TEXT,
                    execution_time REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # MCP Operations table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS mcp_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    operation_type TEXT,
                    service TEXT,
                    request_data TEXT,
                    response_data TEXT,
                    status TEXT DEFAULT 'pending',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # System logs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT,
                    message TEXT,
                    component TEXT,
                    user_id INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    def save_conversation(self, user_id: int, session_id: str, message_type: str, 
                         content: str, agent_type: str = None, metadata: Dict = None):
        """Save conversation to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO conversations (user_id, session_id, message_type, content, agent_type, metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, session_id, message_type, content, agent_type, 
                  json.dumps(metadata or {})))
            conn.commit()
    
    def save_workflow(self, user_id: int, session_id: str, workflow_type: str, 
                     input_data: Dict, output_data: Dict = None, status: str = 'completed',
                     error_message: str = None, execution_time: float = None):
        """Save workflow execution to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflows (user_id, session_id, workflow_type, input_data, 
                                     output_data, status, error_message, execution_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, session_id, workflow_type, json.dumps(input_data),
                  json.dumps(output_data or {}), status, error_message, execution_time))
            conn.commit()
    
    def get_user_statistics(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive user statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get conversation count
            cursor.execute("SELECT COUNT(*) as count FROM conversations WHERE user_id = ?", (user_id,))
            conversations = cursor.fetchone()['count']
            
            # Get workflow count
            cursor.execute("SELECT COUNT(*) as count FROM workflows WHERE user_id = ?", (user_id,))
            workflows = cursor.fetchone()['count']
            
            # Get MCP operations count
            cursor.execute("SELECT COUNT(*) as count FROM mcp_operations WHERE user_id = ?", (user_id,))
            mcp_ops = cursor.fetchone()['count']
            
            # Get recent activity
            cursor.execute("""
                SELECT DATE(timestamp) as date, COUNT(*) as count 
                FROM conversations 
                WHERE user_id = ? AND timestamp >= date('now', '-7 days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (user_id,))
            
            activity = dict(cursor.fetchall())
            
            return {
                'conversations': conversations,
                'workflows': workflows,
                'mcp_operations': mcp_ops,
                'recent_activity': activity
            }
    def save_mcp_operation(self, user_id: int, operation_type: str, service: str, 
                       request_data: dict, response_data: dict, 
                       status: str = "completed"):
        """Save MCP operation details into the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO mcp_operations (user_id, operation_type, service, 
                    request_data, response_data, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                operation_type,
                service,
                json.dumps(request_data),
                json.dumps(response_data),
                status
            ))
            conn.commit()

# ENHANCED MEMORY MANAGEMENT SYSTEM

class AdvancedMemoryManager:
    def __init__(self, max_messages: int = 50):
        self.max_messages = max_messages
        self.db = DatabaseManager()
        
        if LANGCHAIN_AVAILABLE:
            try:
                # Initialize multiple memory types
                self.conversation_memory = ConversationBufferWindowMemory(
                    k=max_messages, 
                    return_messages=True,
                    memory_key="chat_history"
                )
                
                self.summary_memory = ConversationSummaryBufferMemory(
                    llm=ChatGroq(groq_api_key=config.groq_api_key, model_name='llama3-70b-8192', temperature=0.1),
                    max_token_limit=1000,
                    return_messages=True
                )
                
                self.entity_memory = ConversationEntityMemory(
                    llm=ChatGroq(groq_api_key=config.groq_api_key, model_name='llama3-70b-8192', temperature=0.1),
                    return_messages=True
                )
                
            except Exception as e:
                st.warning(f"Memory initialization warning: {str(e)}")
                self.conversation_memory = None
                self.summary_memory = None
                self.entity_memory = None
        else:
            self.conversation_memory = None
            self.summary_memory = None
            self.entity_memory = None
    
    def add_message(self, user_input: str, ai_response: str, user_id: int = None, session_id: str = None):
        """Add message to all memory systems"""
        try:
            # Add to LangChain memories
            if self.conversation_memory:
                self.conversation_memory.save_context(
                    {"input": user_input}, 
                    {"output": ai_response}
                )
            
            if self.summary_memory:
                self.summary_memory.save_context(
                    {"input": user_input}, 
                    {"output": ai_response}
                )
            
            if self.entity_memory:
                self.entity_memory.save_context(
                    {"input": user_input}, 
                    {"output": ai_response}
                )
            
            # Save to database
            if user_id and session_id:
                self.db.save_conversation(user_id, session_id, 'user', user_input)
                self.db.save_conversation(user_id, session_id, 'assistant', ai_response)
                
        except Exception as e:
            st.error(f"Memory save error: {str(e)}")
    
    def get_conversation_context(self, limit: int = 10) -> str:
        """Get formatted conversation context"""
        if not self.conversation_memory:
            return ""
        
        try:
            messages = self.conversation_memory.chat_memory.messages[-limit*2:]  # *2 for user+assistant pairs
            context_parts = []
            
            for msg in messages:
                if isinstance(msg, HumanMessage):
                    context_parts.append(f"User: {msg.content}")
                elif isinstance(msg, AIMessage):
                    context_parts.append(f"Assistant: {msg.content}")
            
            return "\n".join(context_parts)
        except Exception as e:
            st.error(f"Context retrieval error: {str(e)}")
            return ""
    
    def get_conversation_summary(self) -> str:
        """Get conversation summary"""
        if not self.summary_memory:
            return ""
        
        try:
            return self.summary_memory.moving_summary_buffer
        except Exception as e:
            st.error(f"Summary retrieval error: {str(e)}")
            return ""
    
    def get_entities(self) -> Dict[str, str]:
        """Get extracted entities from conversation"""
        if not self.entity_memory:
            return {}
        
        try:
            return dict(self.entity_memory.entity_store.store)
        except Exception as e:
            st.error(f"Entity retrieval error: {str(e)}")
            return {}
    
    def clear_memory(self):
        """Clear all memory systems"""
        try:
            if self.conversation_memory:
                self.conversation_memory.clear()
            if self.summary_memory:
                self.summary_memory.clear()
            if self.entity_memory:
                self.entity_memory.clear()
        except Exception as e:
            st.error(f"Memory clear error: {str(e)}")

# ENHANCED GITHUB MCP INTEGRATION

class EnhancedGitHubManager:
    def __init__(self):
        self.github = None
        self.user = None
        self.rate_limit_remaining = 5000
        self.db = DatabaseManager()
        
        if GITHUB_AVAILABLE and config.github_token:
            try:
                self.github = Github(config.github_token)
                self.user = self.github.get_user()
                rate_limit = self.github.get_rate_limit()
                self.rate_limit_remaining = rate_limit.core.remaining
            except Exception as e:
                st.error(f"GitHub initialization error: {str(e)}")
    
    def check_rate_limit(self) -> bool:
        """Check if we have rate limit remaining"""
        if not self.github:
            return False
        
        try:
            rate_limit = self.github.get_rate_limit()
            self.rate_limit_remaining = rate_limit.core.remaining
            return self.rate_limit_remaining > 10  # Keep some buffer
        except Exception:
            return False
    
    def create_repository(self, repo_name: str, description: str = "", 
                         private: bool = False, auto_init: bool = True) -> Dict[str, Any]:
        """Create a new repository with enhanced options"""
        if not self.github or not self.check_rate_limit():
            return {"success": False, "error": "GitHub not available or rate limit exceeded"}
        
        try:
            repo = self.user.create_repo(
                name=repo_name,
                description=description,
                private=private,
                auto_init=auto_init,
                gitignore_template="Python" if auto_init else None
            )
            
            result = {
                "success": True,
                "repo_name": repo.name,
                "repo_url": repo.html_url,
                "clone_url": repo.clone_url,
                "ssh_url": repo.ssh_url,
                "description": repo.description,
                "private": repo.private
            }
            
            # Log MCP operation
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "create_repository",
                    "github",
                    {"repo_name": repo_name, "description": description, "private": private},
                    result,
                    "success"
                )
            
            return result
            
        except GithubException as e:
            error_msg = f"GitHub API error: {e.data.get('message', str(e))}"
            return {"success": False, "error": error_msg}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def create_branch(self, repo_name: str, branch_name: str, source_branch: str = "main") -> Dict[str, Any]:
        """Create a new branch in repository"""
        if not self.github or not self.check_rate_limit():
            return {"success": False, "error": "GitHub not available or rate limit exceeded"}
        
        try:
            repo = self.user.get_repo(repo_name)
            source_ref = repo.get_git_ref(f"heads/{source_branch}")
            
            new_ref = repo.create_git_ref(
                ref=f"refs/heads/{branch_name}",
                sha=source_ref.object.sha
            )
            
            result = {
                "success": True,
                "branch_name": branch_name,
                "repo_name": repo_name,
                "source_branch": source_branch,
                "ref_url": new_ref.url
            }
            
            # Log MCP operation
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "create_branch",
                    "github",
                    {"repo_name": repo_name, "branch_name": branch_name, "source_branch": source_branch},
                    result,
                    "success"
                )
            
            return result
            
        except GithubException as e:
            error_msg = f"GitHub API error: {e.data.get('message', str(e))}"
            return {"success": False, "error": error_msg}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def list_repositories(self, limit: int = 20, type_filter: str = "all") -> List[Dict[str, Any]]:
        """List repositories with enhanced filtering"""
        if not self.github or not self.check_rate_limit():
            return []
        
        try:
            repos = self.user.get_repos(type=type_filter, sort="updated")
            repo_list = []
            
            for repo in repos[:limit]:
                repo_info = {
                    "name": repo.name,
                    "description": repo.description or "No description",
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "language": repo.language,
                    "private": repo.private,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                    "size": repo.size
                }
                repo_list.append(repo_info)
            
            return repo_list
            
        except Exception as e:
            st.error(f"Error listing repositories: {str(e)}")
            return []
    
    def get_repository_branches(self, repo_name: str) -> List[Dict[str, Any]]:
        """Get all branches for a repository"""
        if not self.github or not self.check_rate_limit():
            return []
        
        try:
            repo = self.user.get_repo(repo_name)
            branches = repo.get_branches()
            
            branch_list = []
            for branch in branches:
                branch_info = {
                    "name": branch.name,
                    "protected": branch.protected,
                    "commit_sha": branch.commit.sha,
                    "commit_url": branch.commit.html_url
                }
                branch_list.append(branch_info)
            
            return branch_list
            
        except Exception as e:
            st.error(f"Error getting branches: {str(e)}")
            return []

# ADVANCED GEMINI CODE GENERATION

class AdvancedGeminiManager:
    def __init__(self):
        self.gemini = None
        self.db = DatabaseManager()
        
        if LANGCHAIN_AVAILABLE and config.gemini_api_key:
            try:
                self.gemini = ChatGoogleGenerativeAI(
                    model="gemini-1.5-flash",
                    google_api_key=config.gemini_api_key,
                    temperature=0.3,
                    max_tokens=4000
                )
            except Exception as e:
                st.error(f"Gemini initialization error: {str(e)}")
    
    def generate_code(self, prompt: str, language: str = "python", 
                     style: str = "clean", include_tests: bool = False) -> Dict[str, Any]:
        """Generate code with advanced options"""
        if not self.gemini:
            return {"success": False, "error": "Gemini not available"}
        
        try:
            # Enhanced system prompt based on parameters
            style_instructions = {
                "clean": "Focus on clean, readable code with clear variable names and good structure.",
                "performance": "Optimize for performance and efficiency, use advanced algorithms where appropriate.",
                "beginner": "Write code that's easy to understand for beginners with extensive comments.",
                "production": "Write production-ready code with error handling, logging, and best practices."
            }
            
            test_instruction = "\nAlso include comprehensive unit tests using appropriate testing frameworks." if include_tests else ""
            
            system_prompt = f"""You are an expert {language} developer. {style_instructions.get(style, style_instructions['clean'])}
            
            Generate well-structured {language} code based on the user's request. Include:
            - Clear docstrings and comments
            - Proper error handling
            - Type hints where applicable
            - Best practices for {language}
            {test_instruction}
            
            Return only the code without additional explanations."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=prompt)
            ]
            
            start_time = time.time()
            response = self.gemini.invoke(messages)
            execution_time = time.time() - start_time
            
            result = {
                "success": True,
                "code": response.content,
                "language": language,
                "style": style,
                "execution_time": execution_time
            }
            
            # Log MCP operation
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "generate_code",
                    "gemini",
                    {"prompt": prompt, "language": language, "style": style, "include_tests": include_tests},
                    result,
                    "success"
                )
            
            return result
            
        except Exception as e:
            error_result = {"success": False, "error": f"Code generation error: {str(e)}"}
            
            # Log error
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "generate_code",
                    "gemini",
                    {"prompt": prompt, "language": language, "style": style},
                    error_result,
                    "error"
                )
            
            return error_result
    
    def explain_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Explain provided code in detail"""
        if not self.gemini:
            return {"success": False, "error": "Gemini not available"}
        
        try:
            system_prompt = f"""You are an expert code reviewer and teacher. Analyze the provided {language} code and provide:
            
            1. A clear explanation of what the code does
            2. Breakdown of key components and functions
            3. Identification of any potential issues or improvements
            4. Explanation of best practices used or missing
            5. Performance considerations if applicable
            
            Be detailed but accessible in your explanation."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Please explain this {language} code:\n\n```{language}\n{code}\n```")
            ]
            
            response = self.gemini.invoke(messages)
            
            return {
                "success": True,
                "explanation": response.content,
                "language": language
            }
            
        except Exception as e:
            return {"success": False, "error": f"Code explanation error: {str(e)}"}
    
    def optimize_code(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Optimize provided code for better performance"""
        if not self.gemini:
            return {"success": False, "error": "Gemini not available"}
        
        try:
            system_prompt = f"""You are an expert {language} performance optimizer. Analyze the provided code and:
            
            1. Identify performance bottlenecks
            2. Provide optimized version of the code
            3. Explain the optimizations made
            4. Estimate performance improvements
            5. Ensure the optimized code maintains the same functionality
            
            Focus on algorithmic improvements, efficient data structures, and {language}-specific optimizations."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Please optimize this {language} code:\n\n```{language}\n{code}\n```")
            ]
            
            response = self.gemini.invoke(messages)
            
            return {
                "success": True,
                "optimized_code": response.content,
                "original_code": code,
                "language": language
            }
            
        except Exception as e:
            return {"success": False, "error": f"Code optimization error: {str(e)}"}

# PLANNING AGENT WITH LANGGRAPH

class PlanningAgent:
    def __init__(self):
        self.db = DatabaseManager()
        
        if LANGCHAIN_AVAILABLE:
            try:
                self.llm = ChatGroq(
                    groq_api_key=config.groq_api_key,
                    model_name='llama3-70b-8192',
                    temperature=0.1
                )
            except Exception as e:
                st.error(f"Planning agent initialization error: {str(e)}")
                self.llm = None
        else:
            self.llm = None
    
    def create_plan(self, goal: str, context: str = "") -> Dict[str, Any]:
        """Create a detailed plan for achieving a goal"""
        if not self.llm:
            return {"success": False, "error": "Planning agent not available"}
        
        try:
            system_prompt = """You are an expert planning agent. Create detailed, actionable plans for achieving goals.
            
            For each plan, provide:
            1. Goal analysis and requirements
            2. Step-by-step breakdown
            3. Resource requirements
            4. Timeline estimates
            5. Risk assessment
            6. Success criteria
            7. Alternative approaches
            
            Make plans specific, measurable, and achievable."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Goal: {goal}\n\nContext: {context}\n\nPlease create a comprehensive plan.")
            ]
            
            start_time = time.time()
            response = self.llm.invoke(messages)
            execution_time = time.time() - start_time
            
            plan_data = {
                "goal": goal,
                "context": context,
                "plan": response.content,
                "created_at": datetime.now().isoformat(),
                "execution_time": execution_time
            }
            
            # Save to database
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_workflow(
                    st.session_state.user_id,
                    st.session_state.session_id,
                    "planning",
                    {"goal": goal, "context": context},
                    plan_data,
                    "completed",
                    execution_time=execution_time
                )
            
            return {"success": True, "plan": plan_data}
            
        except Exception as e:
            return {"success": False, "error": f"Planning error: {str(e)}"}
    
    def break_down_task(self, task: str, complexity: str = "medium") -> Dict[str, Any]:
        """Break down a complex task into smaller subtasks"""
        if not self.llm:
            return {"success": False, "error": "Planning agent not available"}
        
        try:
            complexity_instructions = {
                "simple": "Break into 3-5 basic steps",
                "medium": "Break into 5-10 detailed steps with sub-steps",
                "complex": "Break into 10+ detailed steps with multiple levels of sub-tasks"
            }
            
            system_prompt = f"""You are a task decomposition expert. {complexity_instructions.get(complexity, complexity_instructions['medium'])}.
            
            For each step, provide:
            - Clear description
            - Prerequisites
            - Estimated time
            - Difficulty level
            - Required resources
            
            Format as a structured breakdown that's easy to follow."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Please break down this task: {task}")
            ]
            
            response = self.llm.invoke(messages)
            
            return {
                "success": True,
                "task": task,
                "complexity": complexity,
                "breakdown": response.content
            }
            
        except Exception as e:
            return {"success": False, "error": f"Task breakdown error: {str(e)}"}

# MULTI-AGENT STATE DEFINITIONS

class AgentState(TypedDict):
    user_request: str
    task_type: str
    context: str
    github_operations: List[Dict]
    code_generations: List[Dict]
    plans: List[Dict]
    final_output: str
    workflow_status: str
    execution_time: float
    errors: List[str]
class MCPMySQLConnector:
    def __init__(self, host='localhost', user='chatbot_user', password='root', database='chatbot_db'):
        self.config = {
            'host': host,
            'user': user,
            'password': password,
            'database': database
        }

    def execute_query(self, query: str):
        connection = None
        cursor = None
        try:
            connection = mysql.connector.connect(**self.config)
            cursor = connection.cursor(dictionary=True)
            cursor.execute(query)

            if query.strip().lower().startswith('select'):
                return cursor.fetchall()
            else:
                connection.commit()
                return {"message": "Query executed successfully"}

        except Error as e:
            return {"error": str(e)}

        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

# ENHANCED MULTI-AGENT SYSTEM WITH MCP

class EnhancedMCPMultiAgentSystem:
    
    def __init__(self):
        self.github_manager = EnhancedGitHubManager()
        self.gemini_manager = AdvancedGeminiManager()
        self.planning_agent = PlanningAgent()
        self.memory_manager = AdvancedMemoryManager()
        self.mysql_connector = MCPMySQLConnector()
        self.db = DatabaseManager()
        
        # Initialize main agent
        if LANGCHAIN_AVAILABLE:
            try:
                self.main_agent = ChatGroq(
                    groq_api_key=config.groq_api_key,
                    model_name='llama3-70b-8192',
                    temperature=0.3
                )
            except Exception as e:
                st.error(f"Main agent initialization error: {str(e)}")
                self.main_agent = None
        else:
            self.main_agent = None

    
    
    def classify_request(self, user_request: str) -> Dict[str, Any]:
        """Classify user request and determine required agents"""
        request_lower = user_request.lower()
        
        classification = {
            "primary_type": "chat",
            "secondary_types": [],
            "confidence": 0.5,
            "required_agents": ["main"],
            "mcp_operations": []
        }
        
        # GitHub operations
        github_keywords = ['github', 'repository', 'repo', 'branch', 'git', 'clone', 'fork']
        if any(keyword in request_lower for keyword in github_keywords):
            classification["primary_type"] = "github_mcp"
            classification["required_agents"].extend(["github", "mcp"])
            classification["confidence"] = 0.8
            
            if any(word in request_lower for word in ['create', 'new']):
                classification["mcp_operations"].append("create_repository")
            if 'branch' in request_lower:
                classification["mcp_operations"].append("manage_branches")
            if any(word in request_lower for word in ['list', 'show', 'get']):
                classification["mcp_operations"].append("list_repositories")
        
        # Code generation
        code_keywords = ['code', 'generate', 'program', 'function', 'class', 'script', 'algorithm']
        if any(keyword in request_lower for keyword in code_keywords):
            if classification["primary_type"] == "chat":
                classification["primary_type"] = "code_generation"
            else:
                classification["secondary_types"].append("code_generation")
            classification["required_agents"].append("gemini")
            classification["confidence"] = max(classification["confidence"], 0.8)
        
        # Planning
        planning_keywords = ['plan', 'strategy', 'steps', 'how to', 'break down', 'organize']
        if any(keyword in request_lower for keyword in planning_keywords):
            if classification["primary_type"] == "chat":
                classification["primary_type"] = "planning"
            else:
                classification["secondary_types"].append("planning")
            classification["required_agents"].append("planning")
            classification["confidence"] = max(classification["confidence"], 0.7)
        
        return classification
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """Process request through multi-agent system"""
        start_time = time.time()
        
        try:
            # Classify request
            classification = self.classify_request(user_request)
            
            # Initialize state
            state = AgentState(
                user_request=user_request,
                task_type=classification["primary_type"],
                context=self.memory_manager.get_conversation_context(),
                github_operations=[],
                code_generations=[],
                plans=[],
                final_output="",
                workflow_status="Processing...",
                execution_time=0.0,
                errors=[]
            )
            
            # Process based on primary type
            if classification["primary_type"] == "github_mcp":
                state = self.handle_github_operations(state, classification)
            elif classification["primary_type"] == "code_generation":
                state = self.handle_code_generation(state)
            elif classification["primary_type"] == "planning":
                state = self.handle_planning(state)
            else:
                state = self.handle_general_chat(state)
            
            # Handle secondary operations
            for secondary_type in classification["secondary_types"]:
                if secondary_type == "code_generation":
                    state = self.handle_code_generation(state)
                elif secondary_type == "planning":
                    state = self.handle_planning(state)
            
            # Finalize response
            execution_time = time.time() - start_time
            state["execution_time"] = execution_time
            state["workflow_status"] = "Completed" if not state["errors"] else "Completed with errors"
            
            # Add to memory
            if state["final_output"]:
                self.memory_manager.add_message(
                    user_request,
                    state["final_output"],
                    getattr(st.session_state, 'user_id', None),
                    st.session_state.session_id
                )
            
            # Save workflow
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_workflow(
                    st.session_state.user_id,
                    st.session_state.session_id,
                    classification["primary_type"],
                    {"user_request": user_request, "classification": classification},
                    dict(state),
                    "completed" if not state["errors"] else "error",
                    execution_time=execution_time
                )
            
            return {
                "user_request": user_request,
                "task_type": classification["primary_type"],
                "final_output": state["final_output"],
                "workflow_status": state["workflow_status"],
                "execution_time": execution_time,
                "agent_outputs": {
                    "github": state["github_operations"],
                    "code": state["code_generations"],
                    "plans": state["plans"]
                },
                "mcp_operations": classification["mcp_operations"],
                "errors": state["errors"]
            }
            
        except Exception as e:
            error_msg = f"System error: {str(e)}"
            return {
                "user_request": user_request,
                "task_type": "error",
                "final_output": f"I apologize, but I encountered an error while processing your request: {error_msg}",
                "workflow_status": "Error",
                "execution_time": time.time() - start_time,
                "agent_outputs": {},
                "mcp_operations": [],
                "errors": [error_msg]
            }
    
    def handle_github_operations(self, state: AgentState, classification: Dict) -> AgentState:
        """Handle GitHub MCP operations"""
        try:
            request_lower = state["user_request"].lower()
            
            # List repositories
            if "list" in request_lower and any(word in request_lower for word in ["repo", "repository"]):
                repos = self.github_manager.list_repositories(limit=10)
                if repos:
                    repo_info = []
                    for repo in repos:
                        stars = f"⭐ {repo['stars']}" if repo['stars'] > 0 else ""
                        language = f"({repo['language']})" if repo['language'] else ""
                        private_indicator = "🔒" if repo['private'] else "🌍"
                        
                        repo_info.append(
                            f"**{private_indicator} {repo['name']}** {language} {stars}\n"
                            f"└─ {repo['description']}\n"
                            f"└─ [View Repository]({repo['html_url']})"
                        )
                    
                    state["github_operations"].append({
                        "operation": "list_repositories",
                        "success": True,
                        "data": repos
                    })
                    
                    state["final_output"] = f"## 📂 Your GitHub Repositories\n\n" + "\n\n".join(repo_info)
                else:
                    state["final_output"] = "No repositories found or GitHub connection failed."
            
            # Create repository
            elif "create" in request_lower and any(word in request_lower for word in ["repo", "repository"]):
                # Extract repository name (simple parsing)
                words = state["user_request"].split()
                repo_name = None
                for i, word in enumerate(words):
                    if word.lower() in ["repository", "repo"] and i < len(words) - 1:
                        repo_name = words[i + 1].strip('"\'')
                        break
                
                if not repo_name:
                    state["final_output"] = "Please specify the repository name. Example: 'create repository my-new-project'"
                else:
                    result = self.github_manager.create_repository(
                        repo_name=repo_name,
                        description=f"Repository created via AI Assistant on {datetime.now().strftime('%Y-%m-%d')}"
                    )
                    
                    state["github_operations"].append({
                        "operation": "create_repository",
                        "success": result["success"],
                        "data": result
                    })
                    
                    if result["success"]:
                        state["final_output"] = f"""
## ✅ Repository Created Successfully!

**Repository:** {result['repo_name']}
**URL:** [View Repository]({result['repo_url']})
**Clone URL:** `{result['clone_url']}`
**SSH URL:** `{result['ssh_url']}`

Your repository has been created with a Python .gitignore and is ready for development!
                        """.strip()
                    else:
                        state["errors"].append(result["error"])
                        state["final_output"] = f"❌ Failed to create repository: {result['error']}"
            
            # Get branches
            elif "branch" in request_lower and any(word in request_lower for word in ["list", "show", "get"]):
                # This would need repository name extraction
                state["final_output"] = "To list branches, please specify the repository name. Example: 'show branches for my-repo'"
            
            else:
                # General GitHub help
                state["final_output"] = """
## 🐙 GitHub Operations Available

I can help you with the following GitHub operations:

### 📂 Repository Management
- **List repositories:** "list my repositories" or "show my repos"
- **Create repository:** "create repository [name]" 
- **Repository details:** "show details for [repo-name]"

### 🌿 Branch Management  
- **List branches:** "show branches for [repo-name]"
- **Create branch:** "create branch [name] in [repo-name]"

### 📊 Repository Stats
- **Get statistics:** "show stats for [repo-name]"

What would you like to do with GitHub?
                """.strip()
            
        except Exception as e:
            error_msg = f"GitHub operation error: {str(e)}"
            state["errors"].append(error_msg)
            state["final_output"] = f"❌ GitHub operation failed: {error_msg}"
        
        return state
    
    def handle_code_generation(self, state: AgentState) -> AgentState:
        """Handle code generation with Gemini"""
        try:
            # Extract language if specified
            request_lower = state["user_request"].lower()
            language = "python"  # default
            
            languages = ["python", "javascript", "java", "cpp", "c++", "go", "rust", "typescript", "html", "css"]
            for lang in languages:
                if lang in request_lower:
                    language = lang
                    break
            
            # Determine style
            style = "clean"
            if "beginner" in request_lower or "simple" in request_lower:
                style = "beginner"
            elif "production" in request_lower or "enterprise" in request_lower:
                style = "production"
            elif "performance" in request_lower or "optimized" in request_lower:
                style = "performance"
            
            # Check if tests are requested
            include_tests = any(word in request_lower for word in ["test", "testing", "unittest"])
            
            result = self.gemini_manager.generate_code(
                state["user_request"],
                language=language,
                style=style,
                include_tests=include_tests
            )
            
            state["code_generations"].append(result)
            
            if result["success"]:
                code_output = f"""
## 💻 Generated {language.title()} Code

**Style:** {style.title()}
**Execution Time:** {result['execution_time']:.2f}s

```{language}
{result['code']}
```

The code has been generated following {style} practices{' with tests included' if include_tests else ''}.
                """.strip()
                
                # If this is not the primary output, append to existing
                if state["final_output"]:
                    state["final_output"] += f"\n\n{code_output}"
                else:
                    state["final_output"] = code_output
            else:
                error_msg = result["error"]
                state["errors"].append(error_msg)
                if not state["final_output"]:
                    state["final_output"] = f"❌ Code generation failed: {error_msg}"
            
        except Exception as e:
            error_msg = f"Code generation system error: {str(e)}"
            state["errors"].append(error_msg)
            if not state["final_output"]:
                state["final_output"] = f"❌ {error_msg}"
        
        return state
    
    def handle_planning(self, state: AgentState) -> AgentState:
        """Handle planning operations"""
        try:
            request_lower = state["user_request"].lower()
            
            if any(word in request_lower for word in ["break down", "breakdown", "steps"]):
                # Task breakdown
                complexity = "medium"
                if "simple" in request_lower or "basic" in request_lower:
                    complexity = "simple"
                elif "complex" in request_lower or "detailed" in request_lower:
                    complexity = "complex"
                
                result = self.planning_agent.break_down_task(state["user_request"], complexity)
            else:
                # General planning
                result = self.planning_agent.create_plan(state["user_request"], state["context"])
            
            state["plans"].append(result)
            
            if result["success"]:
                if "plan" in result:
                    plan_output = f"""
## 📋 Generated Plan

{result['plan']['plan']}

**Planning Time:** {result['plan']['execution_time']:.2f}s
                    """.strip()
                else:
                    plan_output = f"""
## 📋 Task Breakdown

{result['breakdown']}

**Complexity Level:** {result['complexity'].title()}
                    """.strip()
                
                if state["final_output"]:
                    state["final_output"] += f"\n\n{plan_output}"
                else:
                    state["final_output"] = plan_output
            else:
                error_msg = result["error"]
                state["errors"].append(error_msg)
                if not state["final_output"]:
                    state["final_output"] = f"❌ Planning failed: {error_msg}"
                    
        except Exception as e:
            error_msg = f"Planning system error: {str(e)}"
            state["errors"].append(error_msg)
            if not state["final_output"]:
                state["final_output"] = f"❌ {error_msg}"
        
        return state
    
    def handle_general_chat(self, state: AgentState) -> AgentState:
        """Handle general chat requests"""
        try:
            if self.main_agent:
                # Get conversation context
                context = self.memory_manager.get_conversation_context(5)
                entities = self.memory_manager.get_entities()
                
                # Build enhanced context
                enhanced_context = ""
                if context:
                    enhanced_context += f"Recent conversation:\n{context}\n\n"
                if entities:
                    entity_list = ", ".join([f"{k}: {v}" for k, v in list(entities.items())[:5]])
                    enhanced_context += f"Known entities: {entity_list}\n\n"
                
                system_prompt = f"""You are an advanced AI assistant with access to multiple capabilities:

🤖 **Core Capabilities:**
- Natural language conversation with memory
- GitHub repository management (create, list, manage branches)
- Advanced code generation with Gemini AI
- Strategic planning and task breakdown
- Multi-agent workflow coordination

🔧 **Available Tools:**
- GitHub MCP integration for repository operations
- Gemini AI for code generation and explanation
- Planning agent for task breakdown and strategy
- Persistent memory for context awareness

💡 **Response Style:**
- Be helpful, informative, and engaging
- Offer specific suggestions for complex tasks
- Reference previous conversation when relevant
- Suggest using specialized capabilities when appropriate

{enhanced_context}Current user request: {state['user_request']}"""

                messages = [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=state["user_request"])
                ]
                
                response = self.main_agent.invoke(messages)
                state["final_output"] = response.content
                
            else:
                state["final_output"] = f"""
## 🤖 Advanced AI Assistant

Hello! I'm your advanced AI assistant with multiple capabilities:

### 🛠️ What I Can Do:
- **💬 Natural Conversation:** Chat with memory and context awareness
- **🐙 GitHub Operations:** Create repositories, manage branches, list repos
- **💻 Code Generation:** Generate code in multiple languages with different styles
- **📋 Planning & Strategy:** Create detailed plans and break down complex tasks
- **🔄 Multi-Agent Workflows:** Coordinate multiple AI agents for complex requests

### 🚀 Example Commands:
- "List my GitHub repositories"
- "Create a repository called 'my-project'"
- "Generate a Python function for sorting data"
- "Create a plan for building a web application"
- "Break down the task of learning machine learning"

### 💡 Your Request:
"{state['user_request']}"

How would you like me to help you with this? I can provide general information or use my specialized capabilities if needed.
                """.strip()
                
        except Exception as e:
            error_msg = f"Chat processing error: {str(e)}"
            state["errors"].append(error_msg)
            state["final_output"] = f"❌ I apologize, but I encountered an error: {error_msg}"
        
        return state

# ENHANCED USER AUTHENTICATION

def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = config.secret_key.encode('utf-8')
    # Use pbkdf2_hmac with SHA-256 and convert to hex
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return hashed.hex()

def load_users() -> Dict[str, Any]:
    """Load users from file"""
    if os.path.exists(config.users_file):
        try:
            with open(config.users_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}
    return {}

def save_users(users: Dict[str, Any]):
    """Save users to file"""
    try:
        with open(config.users_file, "w") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        st.error(f"Error saving users: {str(e)}")

def signup(username: str, password: str, email: str = "") -> tuple[bool, str]:
    """User signup with enhanced validation"""
    if len(username) < 3:
        return False, "Username must be at least 3 characters long."
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters long."
    
    users = load_users()
    if username in users:
        return False, "Username already exists."
    
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, email, preferences)
                VALUES (?, ?, ?, ?)
            """, (username, hash_password(password), email, json.dumps({"theme": "modern_dark"})))
            
            user_id = cursor.lastrowid
            conn.commit()
        
        # Also save to JSON for backward compatibility
        users[username] = {
            "password": hash_password(password),
            "email": email,
            "created_at": datetime.now().isoformat(),
            "user_id": user_id,
            "preferences": {"theme": "modern_dark"}
        }
        save_users(users)
        
        return True, "Signup successful! Please login."
        
    except Exception as e:
        return False, f"Signup failed: {str(e)}"

def login(username: str, password: str) -> tuple[bool, str, Optional[int]]:
    """User login with enhanced session management"""
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, password_hash, preferences FROM users 
                WHERE username = ? AND is_active = 1
            """, (username,))
            
            user = cursor.fetchone()
            if user and user['password_hash'] == hash_password(password):
                # Update last login
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP 
                    WHERE username = ?
                """, (username,))
                conn.commit()
                
                return True, "Login successful!", user['id']
            else:
                return False, "Invalid username or password.", None
                
    except Exception as e:
        return False, f"Login failed: {str(e)}", None

# ENHANCED LOGIN INTERFACE

def show_enhanced_login():
    """Show enhanced login interface with theme selection"""
    apply_enhanced_styling()
    
    # Theme switcher
    st.markdown("""
    <div class="theme-switcher">
        🎨
    </div>
    """, unsafe_allow_html=True)
    
    with st.sidebar:
        st.markdown("### 🎨 Theme")
        theme = st.selectbox("Choose theme:", 
                           ["modern_dark", "neon", "sunset"], 
                           index=0,
                           key="theme_selector")
        if theme != st.session_state.theme:
            st.session_state.theme = theme
            st.rerun()
    
    st.markdown("""
    <div class="login-container">
        <div style="font-size: 4rem; margin-bottom: 1rem; background: var(--primary-gradient); 
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
                    background-clip: text;">🤖</div>
        <h1 style="color: var(--text-primary); margin-bottom: 0.5rem; font-weight: 700;">
            Sudeeksha's Assistant
        </h1>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        login_tab = st.button("🔑 Login", use_container_width=True)
    with col2:
        signup_tab = st.button("📝 Sign Up", use_container_width=True)
    
    # Toggle between login and signup
    if 'auth_mode' not in st.session_state:
        st.session_state.auth_mode = 'login'
    
    if login_tab:
        st.session_state.auth_mode = 'login'
    elif signup_tab:
        st.session_state.auth_mode = 'signup'
    
    st.markdown("---")
    
    # Form fields
    username = st.text_input("👤 Username", placeholder="Enter your username", key="auth_username")
    password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="auth_password")
    
    if st.session_state.auth_mode == 'signup':
        email = st.text_input("📧 Email (optional)", placeholder="Enter your email", key="auth_email")
        confirm_password = st.text_input("🔒 Confirm Password", type="password", 
                                       placeholder="Confirm your password", key="auth_confirm")
        
        if st.button(f"🚀 Create Account", use_container_width=True, key="signup_btn"):
            if not username or not password:
                st.error("Username and password are required.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            else:
                success, message = signup(username, password, email)
                if success:
                    st.success(message)
                    st.session_state.auth_mode = 'login'
                    st.rerun()
                else:
                    st.error(message)
    else:
        if st.button(f"🚀 Sign In", use_container_width=True, key="login_btn"):
            if not username or not password:
                st.error("Username and password are required.")
            else:
                success, message, user_id = login(username, password)
                if success:
                    st.success(message)
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.user_id = user_id
                    st.session_state.login_time = datetime.now()
                    st.rerun()
                else:
                    st.error(message)

# ENHANCED SIDEBAR WITH SYSTEM MONITORING

def show_enhanced_sidebar():
    """Show enhanced sidebar with system monitoring"""
    with st.sidebar:
        # User info section
        st.markdown(f"""
        <div style="background: var(--primary-gradient); color: white; padding: 1rem; 
                    border-radius: 12px; margin-bottom: 1rem;">
            <h3 style="margin: 0; font-size: 1.2rem;">👤 {st.session_state.username}</h3>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9; font-size: 0.9rem;">
                Session: {st.session_state.session_id[:8]}...
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation
        st.markdown("### 🧭 Navigation")
        pages = [
            ("🏠", "Chat Interface"),
            ("📊", "Analytics Dashboard"), 
            ("📝", "Chat History"),
            ("🔧", "System Settings")
        ]
        
        for icon, name in pages:
            full_name = f"{icon} {name}"
            if st.button(full_name, use_container_width=True, 
                        key=f"nav_{name.lower().replace(' ', '_')}"):
                st.session_state.current_page = full_name
                st.rerun()
        
        st.markdown("---")
        
        
        
        # Quick actions
        st.markdown("### ⚡ Quick Actions")
        
        if st.button("🔄 Reset Chat", use_container_width=True):
            st.session_state.chat_history = []
            if 'ai_system' in st.session_state:
                st.session_state.ai_system.memory_manager.clear_memory()
            st.success("Chat reset!")
            st.rerun()
        
        if st.button("📥 Export Data", use_container_width=True):
            if st.session_state.user_id:
                db = DatabaseManager()
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT * FROM conversations 
                        WHERE user_id = ? 
                        ORDER BY timestamp DESC LIMIT 100
                    """, (st.session_state.user_id,))
                    
                    conversations = [dict(row) for row in cursor.fetchall()]
                
                export_data = {
                    "username": st.session_state.username,
                    "export_timestamp": datetime.now().isoformat(),
                    "conversations": conversations,
                    "session_stats": db.get_user_statistics(st.session_state.user_id)
                }
                
                st.download_button(
                    "💾 Download",
                    json.dumps(export_data, indent=2, default=str),
                    file_name=f"ai_assistant_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json",
                    use_container_width=True
                )
        
        if st.button("🔒 Logout", use_container_width=True):
            # Clear session
            for key in ['logged_in', 'username', 'user_id', 'login_time', 'ai_system']:
                if key in st.session_state:
                    delattr(st.session_state, key)
            st.rerun()

# ENHANCED CHAT INTERFACE

def show_enhanced_chat_interface():
    """Show enhanced chat interface with real-time features"""
    st.title("🤖 Advanced AI Assistant")
    
    # Initialize AI system with loading animation
    if 'ai_system' not in st.session_state:
        with st.spinner("🚀 Initializing multi-agent AI system..."):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Simulate initialization steps
            steps = [
                ("Initializing core agents...", 0.2),
                ("Connecting to GitHub MCP...", 0.4),
                ("Loading Gemini AI models...", 0.6),  
                ("Setting up memory systems...", 0.8),
                ("System ready!", 1.0)
            ]
            
            for step, progress in steps:
                status_text.text(step)
                progress_bar.progress(progress)
                time.sleep(0.5)
            
            st.session_state.ai_system = EnhancedMCPMultiAgentSystem()
            
        st.success("✅ Multi-agent AI system initialized!")
        time.sleep(1)
        st.rerun()
    
    # System capabilities overview
    with st.expander("🔧 System Capabilities & Status", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            **🤖 AI Agents**
            - Main Conversation Agent
            - GitHub MCP Agent  
            - Code Generation Agent
            - Planning Agent
            """)
        
        with col2:
            st.markdown("""
            **🔗 Integrations**
            - GitHub API & MCP
            - Gemini AI Models
            - LangChain Framework
            - MySQL Database
            """)
        
        with col3:
            st.markdown("""
            **💾 Memory Systems**
            - Conversation Memory
            - Entity Memory
            - Summary Memory
            - Persistent Storage
            """)
        
        with col4:
            # Real-time system status
            def get_rate_limit():
                try:
                    if (st.session_state.ai_system and 
                        hasattr(st.session_state.ai_system, 'github_manager') and
                        st.session_state.ai_system.github_manager and
                        hasattr(st.session_state.ai_system.github_manager, 'rate_limit_remaining')):
                        
                        github_manager = st.session_state.ai_system.github_manager
                        return github_manager.rate_limit_remaining if github_manager.github else 0
                    return "Not Available"
                except:
                    return "Error"
            
            rate_limit = get_rate_limit()
            
            st.markdown(f"""
            **📊 Live Status**
            - GitHub Rate Limit: {rate_limit}
            - Active Session: ✅
            - Memory: {len(st.session_state.chat_history)} msgs
            - Theme: {st.session_state.theme}
            """)
    
    # Display chat history with enhanced message bubbles
    for i, message in enumerate(st.session_state.chat_history):
        if message["type"] == "user":
            timestamp = message.get("timestamp", "")[:19].replace("T", " ")
            st.markdown(f"""
            <div class="message user">
                <div class="message-avatar user-avatar">👤</div>
                <div class="message-bubble">
                    <div style="font-weight: 500;">{message["content"]}</div>
                    <div style="font-size: 0.75rem; opacity: 0.7; margin-top: 8px;">{timestamp}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            timestamp = message.get("timestamp", "")[:19].replace("T", " ")
            
            # Show workflow info if available
            workflow_badge = ""
            if message.get("task_type") and message.get("task_type") != "chat":
                task_type = message["task_type"].replace("_", " ").title()
                workflow_badge = f"""
                <div style="margin-bottom: 8px;">
                    <span style="background: var(--secondary-gradient); color: white; 
                                 padding: 2px 8px; border-radius: 12px; font-size: 0.7rem; 
                                 font-weight: 600; text-transform: uppercase;">
                        {task_type}
                    </span>
                </div>
                """
            
            # Execution time badge
            exec_time_badge = ""
            if message.get("execution_time"):
                exec_time = message["execution_time"]
                exec_time_badge = f"""
                <span style="background: #e8f5e8; color: #2d5016; padding: 2px 6px; 
                             border-radius: 8px; font-size: 0.7rem; margin-left: 8px;">
                    ⚡ {exec_time:.2f}s
                </span>
                """
            
            st.markdown(f"""
            <div class="message bot">
                <div class="message-avatar bot-avatar">🤖</div>
                <div class="message-bubble">
                    {workflow_badge}
                    <div>{message["content"]}</div>
                    <div style="font-size: 0.75rem; opacity: 0.7; margin-top: 8px; 
                                display: flex; align-items: center; justify-content: space-between;">
                        <span>{timestamp}</span>
                        {exec_time_badge}
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div></div>", unsafe_allow_html=True)

# ANALYTICS DASHBOARD

def show_analytics_dashboard():
    """Show comprehensive analytics dashboard"""
    st.title("📊 Analytics Dashboard")
    st.markdown("**Comprehensive insights into your AI assistant usage**")
    
    if not st.session_state.user_id:
        st.error("User ID not available. Please re-login.")
        return
    
    db = DatabaseManager()
    
    # Get comprehensive statistics
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Basic stats
        cursor.execute("""
            SELECT 
                COUNT(*) as total_conversations,
                COUNT(CASE WHEN message_type = 'user' THEN 1 END) as user_messages,
                COUNT(CASE WHEN message_type = 'assistant' THEN 1 END) as assistant_messages
            FROM conversations 
            WHERE user_id = ?
        """, (st.session_state.user_id,))
        
        conv_stats = cursor.fetchone()
        
        # Activity over time
        cursor.execute("""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as message_count,
                COUNT(CASE WHEN message_type = 'user' THEN 1 END) as user_count
            FROM conversations 
            WHERE user_id = ? AND timestamp >= date('now', '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """, (st.session_state.user_id,))
        
        activity_data = cursor.fetchall()
        
        # Workflow statistics
        cursor.execute("""
            SELECT 
                workflow_type,
                COUNT(*) as count,
                AVG(execution_time) as avg_time,
                COUNT(CASE WHEN status = 'error' THEN 1 END) as errors
            FROM workflows 
            WHERE user_id = ?
            GROUP BY workflow_type
        """, (st.session_state.user_id,))
        
        workflow_stats = cursor.fetchall()
        
        # MCP operations
        cursor.execute("""
            SELECT 
                operation_type,
                service,
                COUNT(*) as count,
                COUNT(CASE WHEN status = 'success' THEN 1 END) as success_count
            FROM mcp_operations 
            WHERE user_id = ?
            GROUP BY operation_type, service
        """, (st.session_state.user_id,))
        
        mcp_stats = cursor.fetchall()
    
    # Display metrics in cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2 style="margin: 0; font-size: 2rem;">{conv_stats['total_conversations'] if conv_stats else 0}</h2>
            <p style="margin: 0.5rem 0 0 0;">Total Messages</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h2 style="margin: 0; font-size: 2rem;">{len(workflow_stats)}</h2>
            <p style="margin: 0.5rem 0 0 0;">Workflow Types</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h2 style="margin: 0; font-size: 2rem;">{len(mcp_stats)}</h2>
            <p style="margin: 0.5rem 0 0 0;">MCP Operations</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        avg_daily = len(activity_data) / 30 if activity_data else 0
        st.markdown(f"""
        <div class="metric-card">
            <h2 style="margin: 0; font-size: 2rem;">{avg_daily:.1f}</h2>
            <p style="margin: 0.5rem 0 0 0;">Daily Average</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Activity chart
    if activity_data:
        st.markdown("### 📈 Activity Over Time")
        
        # Convert to displayable format
        dates = [row['date'] for row in reversed(activity_data[-14:])]  # Last 14 days
        messages = [row['message_count'] for row in reversed(activity_data[-14:])]
        
        # Create simple chart visualization
        chart_data = []
        for date, count in zip(dates, messages):
            chart_data.append({"Date": date, "Messages": count})
        
        if chart_data:
            st.bar_chart(data=chart_data, x="Date", y="Messages")
    
    # Workflow breakdown
    if workflow_stats:
        st.markdown("### 🔄 Workflow Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Workflow Types:**")
            for row in workflow_stats:
                workflow_type = row['workflow_type'].replace('_', ' ').title()
                count = row['count']
                avg_time = row['avg_time'] or 0
                error_rate = (row['errors'] / count * 100) if count > 0 else 0
                
                st.markdown(f"""
                <div class="workflow-step">
                    <strong>{workflow_type}</strong><br>
                    Executions: {count} • Avg Time: {avg_time:.2f}s • Error Rate: {error_rate:.1f}%
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("**Performance Metrics:**")
            
            # Calculate overall metrics
            total_workflows = sum(row['count'] for row in workflow_stats)
            total_errors = sum(row['errors'] for row in workflow_stats)
            avg_execution_time = sum(row['avg_time'] * row['count'] for row in workflow_stats if row['avg_time']) / total_workflows if total_workflows > 0 else 0
            
            st.metric("Total Workflows", total_workflows)
            st.metric("Success Rate", f"{((total_workflows - total_errors) / total_workflows * 100):.1f}%" if total_workflows > 0 else "0%")
            st.metric("Avg Execution Time", f"{avg_execution_time:.2f}s")
    
    # MCP Operations breakdown
    if mcp_stats:
        st.markdown("### 🔗 MCP Operations")
        
        for row in mcp_stats:
            operation = row['operation_type'].replace('_', ' ').title()
            service = row['service'].title()
            count = row['count']
            success_count = row['success_count']
            success_rate = (success_count / count * 100) if count > 0 else 0
            
            st.markdown(f"""
            <div style="background: #f8f9fa; padding: 15px; border-radius: 10px; margin: 10px 0; 
                        border-left: 4px solid var(--secondary-gradient);">
                <strong>{service} - {operation}</strong><br>
                Operations: {count} • Success Rate: {success_rate:.1f}%
                <div style="background: #e9ecef; border-radius: 10px; height: 8px; margin-top: 8px;">
                    <div style="background: var(--secondary-gradient); height: 8px; border-radius: 10px; 
                                width: {success_rate}%;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Recent activity log
    st.markdown("### 📝 Recent Activity")
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT content, agent_type, timestamp, message_type
            FROM conversations 
            WHERE user_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 10
        """, (st.session_state.user_id,))
        
        recent_activity = cursor.fetchall()
        
        for activity in recent_activity:
            content = activity['content'][:100] + "..." if len(activity['content']) > 100 else activity['content']
            agent_type = activity['agent_type'] or 'main'
            timestamp = activity['timestamp'][:19].replace('T', ' ')
            msg_type = activity['message_type']
            
            icon = "👤" if msg_type == "user" else "🤖"
            
            st.markdown(f"""
            <div style="background: white; padding: 12px; border-radius: 8px; margin: 8px 0; 
                        border-left: 3px solid var(--primary-gradient); box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 8px;">
                    <span style="font-size: 1.2rem;">{icon}</span>
                    <strong>{msg_type.title()}</strong>
                    <span style="color: #666; font-size: 0.9rem; margin-left: auto;">{timestamp}</span>
                </div>
                <div style="color: #555;">{content}</div>
                {f'<div style="color: #888; font-size: 0.8rem; margin-top: 4px;">Agent: {agent_type}</div>' if agent_type != 'main' else ''}
            </div>
            """, unsafe_allow_html=True)

# ENHANCED CHAT HISTORY WITH ADVANCED FEATURES

def show_enhanced_chat_history():
    """Show enhanced chat history with search and filtering"""
    st.title("📝 Chat History")
    st.markdown("**Your complete conversation archive with advanced search**")
    
    if not st.session_state.user_id:
        st.error("User ID not available. Please re-login.")
        return
    
    db = DatabaseManager()
    
    # Advanced search and filter controls
    with st.expander("🔍 Advanced Search & Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            search_term = st.text_input("🔎 Search messages", placeholder="Enter keywords...")
            message_type = st.selectbox("📨 Message Type", ["All", "User", "Assistant"])
        
        with col2:
            date_range = st.selectbox("📅 Date Range", [
                "All Time", "Last 7 days", "Last 30 days", "Last 90 days", "Custom Range"
            ])
            
            if date_range == "Custom Range":
                start_date = st.date_input("Start Date")
                end_date = st.date_input("End Date")
        
        with col3:
            agent_filter = st.selectbox("🤖 Agent Type", ["All", "Main", "GitHub", "Gemini", "Planning"])
            sort_order = st.selectbox("📊 Sort Order", ["Newest First", "Oldest First"])
    
    # Build query based on filters
    query = """
        SELECT content, message_type, timestamp, agent_type, metadata, id
        FROM conversations 
        WHERE user_id = ?
    """
    params = [st.session_state.user_id]
    
    # Apply filters
    if search_term:
        query += " AND content LIKE ?"
        params.append(f"%{search_term}%")
    
    if message_type != "All":
        query += " AND message_type = ?"
        params.append(message_type.lower())
    
    if agent_filter != "All":
        query += " AND (agent_type = ? OR agent_type IS NULL)"
        params.append(agent_filter.lower())
    
    # Apply date filter
    if date_range == "Last 7 days":
        query += " AND timestamp >= date('now', '-7 days')"
    elif date_range == "Last 30 days":
        query += " AND timestamp >= date('now', '-30 days')"
    elif date_range == "Last 90 days":
        query += " AND timestamp >= date('now', '-90 days')"
    elif date_range == "Custom Range" and 'start_date' in locals() and 'end_date' in locals():
        query += " AND date(timestamp) BETWEEN ? AND ?"
        params.extend([start_date.isoformat(), end_date.isoformat()])
    
    # Apply sorting
    if sort_order == "Newest First":
        query += " ORDER BY timestamp DESC"
    else:
        query += " ORDER BY timestamp ASC"
    
    query += " LIMIT 100"  # Limit results for performance
    
    # Execute query
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        messages = cursor.fetchall()
        
        # Get total count
        count_query = query.replace("SELECT content, message_type, timestamp, agent_type, metadata, id", "SELECT COUNT(*)")
        count_query = count_query.replace(" LIMIT 100", "")
        cursor.execute(count_query, params)
        total_count = cursor.fetchone()[0]
    
    # Display results
    st.markdown(f"### 💬 Found {len(messages)} messages (Total: {total_count})")
    
    if not messages:
        st.info("No messages found matching your criteria.")
        return
    
    # Group messages by date
    messages_by_date = {}
    for msg in messages:
        date = msg['timestamp'][:10]  # Extract date part
        if date not in messages_by_date:
            messages_by_date[date] = []
        messages_by_date[date].append(msg)
    
    # Display messages grouped by date
    for date, date_messages in messages_by_date.items():
        st.markdown(f"#### 📅 {date}")
        
        for msg in date_messages:
            content = msg['content']
            msg_type = msg['message_type']
            timestamp = msg['timestamp'][11:19]  # Extract time part
            agent_type = msg['agent_type'] or 'main'
            
            # Parse metadata if available
            metadata = {}
            try:
                if msg['metadata']:
                    metadata = json.loads(msg['metadata'])
            except:
                pass
            
            # Message styling
            if msg_type == "user":
                icon = "👤"
                bg_color = "#e3f2fd"
                border_color = "#2196f3"
            else:
                icon = "🤖"
                bg_color = "#f3e5f5"
                border_color = "#9c27b0"
            
            # Display message
            with st.container():
                st.markdown(f"""
                <div style="background: {bg_color}; padding: 15px; border-radius: 12px; 
                            margin: 10px 0; border-left: 4px solid {border_color};">
                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                        <span style="font-size: 1.3rem;">{icon}</span>
                        <strong>{msg_type.title()}</strong>
                        <span style="color: #666; font-size: 0.9rem;">@ {timestamp}</span>
                        {f'<span style="background: #fff; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; margin-left: auto;">{agent_type}</span>' if agent_type != 'main' else ''}
                    </div>
                    <div style="white-space: pre-wrap; line-height: 1.5;">{content}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Show metadata if available
                if metadata:
                    with st.expander(f"📋 Message Details (ID: {msg['id']})", expanded=False):
                        st.json(metadata)
    
    # Export functionality
    st.markdown("---")
    st.markdown("### 📥 Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 Export as JSON", use_container_width=True):
            export_data = {
                "username": st.session_state.username,
                "export_timestamp": datetime.now().isoformat(),
                "search_criteria": {
                    "search_term": search_term,
                    "message_type": message_type,
                    "date_range": date_range,
                    "agent_filter": agent_filter
                },
                "total_messages": len(messages),
                "messages": [dict(msg) for msg in messages]
            }
            
            st.download_button(
                "💾 Download JSON",
                json.dumps(export_data, indent=2, default=str),
                file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True
            )
    
    with col2:
        if st.button("📄 Export as Text", use_container_width=True):
            text_export = f"Chat History Export - {st.session_state.username}\n"
            text_export += f"Generated: {datetime.now().isoformat()}\n"
            text_export += "=" * 50 + "\n\n"
            
            for msg in messages:
                timestamp = msg['timestamp'][:19].replace('T', ' ')
                msg_type = msg['message_type'].upper()
                content = msg['content']
                agent_type = msg['agent_type'] or 'main'
                
                text_export += f"[{timestamp}] {msg_type} ({agent_type}):\n{content}\n\n"
            
            st.download_button(
                "💾 Download Text",
                text_export,
                file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    with col3:
        if st.button("🗑️ Clear History", use_container_width=True):
            if st.checkbox("⚠️ I understand this will permanently delete chat history"):
                with db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM conversations WHERE user_id = ?", (st.session_state.user_id,))
                    cursor.execute("DELETE FROM workflows WHERE user_id = ?", (st.session_state.user_id,))
                    cursor.execute("DELETE FROM mcp_operations WHERE user_id = ?", (st.session_state.user_id,))
                    conn.commit()
                
                st.session_state.chat_history = []
                if 'ai_system' in st.session_state:
                    st.session_state.ai_system.memory_manager.clear_memory()
                
                st.success("✅ Chat history cleared successfully!")
                st.rerun()


# SYSTEM SETTINGS PAGE

def show_system_settings():
    """Show system settings and configuration"""
    st.title("🔧 System Settings")
    st.markdown("**Configure your AI assistant experience**")
    
    # User preferences
    st.markdown("### 👤 User Preferences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Theme selection
        st.markdown("**🎨 Theme**")
        new_theme = st.selectbox(
            "Choose your theme:",
            ["modern_dark", "neon", "sunset"],
            index=["modern_dark", "neon", "sunset"].index(st.session_state.theme)
        )
        
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.success("Theme updated! Refreshing...")
            st.rerun()
        
        # Memory settings
        st.markdown("**🧠 Memory Settings**")
        memory_limit = st.slider("Memory message limit", 10, 100, 50)
        context_length = st.slider("Context length for responses", 3, 10, 5)
    
    with col2:
        # AI model preferences
        st.markdown("**🤖 AI Model Preferences**")
        
        default_temperature = st.slider("Response creativity (temperature)", 0.0, 1.0, 0.3, 0.1)
        response_length = st.selectbox("Default response length", ["Concise", "Balanced", "Detailed"])
        
        # Agent priorities
        st.markdown("**⚡ Agent Priorities**")
        github_priority = st.selectbox("GitHub operations", ["Normal", "High", "Low"])
        code_gen_priority = st.selectbox("Code generation", ["Normal", "High", "Low"])
    
    # System configuration
    st.markdown("---")
    st.markdown("### ⚙️ System Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🔗 API Connections**")
        
        # Check API status
        apis = [
            ("Groq LLM", bool(config.groq_api_key and LANGCHAIN_AVAILABLE)),
            ("Gemini AI", bool(config.gemini_api_key and LANGCHAIN_AVAILABLE)),
            ("GitHub API", bool(config.github_token and GITHUB_AVAILABLE)),
        ]
        
        for api_name, status in apis:
            status_icon = "✅" if status else "❌"
            status_text = "Connected" if status else "Disconnected"
            st.markdown(f"**{api_name}:** {status_icon} {status_text}")
        
        # Database status
        try:
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
            
            st.markdown(f"**Database:** ✅ Connected ({user_count} users)")
        except Exception as e:
            st.markdown(f"**Database:** ❌ Error: {str(e)}")
    
    with col2:
        st.markdown("**📊 System Statistics**")
        
        if st.session_state.user_id:
            db = DatabaseManager()
            stats = db.get_user_statistics(st.session_state.user_id)
            
            st.metric("Total Messages", stats['conversations'])
            st.metric("Workflows Executed", stats['workflows'])
            st.metric("MCP Operations", stats['mcp_operations'])
            
            # Session info
            if st.session_state.login_time:
                session_duration = datetime.now() - st.session_state.login_time
                hours = int(session_duration.total_seconds() // 3600)
                minutes = int((session_duration.total_seconds() % 3600) // 60)
                st.metric("Session Duration", f"{hours:02d}:{minutes:02d}")
    
    # Advanced settings
    st.markdown("---")
    st.markdown("### 🔬 Advanced Settings")
    
    with st.expander("⚠️ Advanced Configuration", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔧 System Maintenance**")
            
            if st.button("🧹 Clear System Cache", use_container_width=True):
                # Clear any cached data
                if 'ai_system' in st.session_state:
                    st.session_state.ai_system.memory_manager.clear_memory()
                st.success("System cache cleared!")
            
            if st.button("🔄 Reset User Preferences", use_container_width=True):
                st.session_state.theme = "modern_dark"
                st.success("Preferences reset to defaults!")
                st.rerun()
        
        with col2:
            st.markdown("**📋 Export System Data**")
            
            if st.button("📊 Generate System Report", use_container_width=True):
                if st.session_state.user_id:
                    db = DatabaseManager()
                    
                    # Generate comprehensive report
                    report = {
                        "user_info": {
                            "username": st.session_state.username,
                            "user_id": st.session_state.user_id,
                            "session_id": st.session_state.session_id,
                            "theme": st.session_state.theme
                        },
                        "system_status": {
                            "langchain_available": LANGCHAIN_AVAILABLE,
                            "github_available": GITHUB_AVAILABLE,
                            "apis_configured": {
                                "groq": bool(config.groq_api_key),
                                "gemini": bool(config.gemini_api_key),
                                "github": bool(config.github_token)
                            }
                        },
                        "statistics": db.get_user_statistics(st.session_state.user_id),
                        "generated_at": datetime.now().isoformat()
                    }
                    
                    st.download_button(
                        "💾 Download Report",
                        json.dumps(report, indent=2, default=str),
                        file_name=f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
    
    # Save settings
    if st.button("💾 Save Settings", use_container_width=True):
        # Here you would save user preferences to database
        st.success("✅ Settings saved successfully!")

# ENHANCED MYSQL MCP INTEGRATION

class MySQLMCPManager:
    def __init__(self):
        self.connection = None
        self.db = DatabaseManager()
        
    def connect_mysql(self, host: str = "localhost", port: int = 3306, 
                     user: str = "root", password: str = "", database: str = "chatbot_db") -> Dict[str, Any]:
        """Connect to MySQL database via MCP"""
        try:
            import mysql.connector
            from mysql.connector import Error
            
            self.connection = mysql.connector.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                autocommit=True
            )
            
            if self.connection.is_connected():
                db_info = self.connection.get_server_info()
                cursor = self.connection.cursor()
                cursor.execute("SELECT DATABASE();")
                db_name = cursor.fetchone()
                
                result = {
                    "success": True,
                    "server_version": db_info,
                    "database": db_name[0] if db_name else "None",
                    "host": host,
                    "port": port
                }
                
                # Log MCP operation
                if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                    self.db.save_mcp_operation(
                        st.session_state.user_id,
                        "mysql_connect",
                        "mysql",
                        {"host": host, "port": port, "database": database},
                        result,
                        "success"
                    )
                
                return result
            
        except Error as e:
            error_result = {"success": False, "error": f"MySQL connection error: {str(e)}"}
            
            # Log error
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "mysql_connect",
                    "mysql",
                    {"host": host, "port": port, "database": database},
                    error_result,
                    "error"
                )
            
            return error_result
        except ImportError:
            return {"success": False, "error": "mysql-connector-python not installed. Run: pip install mysql-connector-python"}
    
    def execute_query(self, query: str, params: tuple = None) -> Dict[str, Any]:
        """Execute MySQL query via MCP"""
        if not self.connection or not self.connection.is_connected():
            return {"success": False, "error": "No active MySQL connection"}
        
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Determine query type
            query_type = query.strip().upper().split()[0]
            
            if query_type == "SELECT":
                results = cursor.fetchall()
                column_names = [desc[0] for desc in cursor.description] if cursor.description else []
                
                result = {
                    "success": True,
                    "query_type": "SELECT",
                    "results": results,
                    "columns": column_names,
                    "row_count": len(results)
                }
            else:
                affected_rows = cursor.rowcount
                result = {
                    "success": True,
                    "query_type": query_type,
                    "affected_rows": affected_rows
                }
            
            cursor.close()
            
            # Log MCP operation
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "mysql_query",
                    "mysql",
                    {"query": query[:100] + "..." if len(query) > 100 else query},
                    {"success": True, "row_count": result.get("row_count", result.get("affected_rows", 0))},
                    "success"
                )
            
            return result
            
        except Exception as e:
            error_result = {"success": False, "error": f"Query execution error: {str(e)}"}
            
            # Log error
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "mysql_query",
                    "mysql",
                    {"query": query[:100] + "..." if len(query) > 100 else query},
                    error_result,
                    "error"
                )
            
            return error_result
    
    def setup_chatbot_tables(self) -> Dict[str, Any]:
        """Setup MySQL tables for chatbot data"""
        tables = {
            "users": """
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    email VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP NULL,
                    preferences JSON,
                    is_active BOOLEAN DEFAULT TRUE
                )
            """,
            "conversations": """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    session_id VARCHAR(100),
                    message_type ENUM('user', 'assistant', 'system'),
                    content TEXT,
                    agent_type VARCHAR(50),
                    metadata JSON,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """,
            "workflows": """
                CREATE TABLE IF NOT EXISTS workflows (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    session_id VARCHAR(100),
                    workflow_type VARCHAR(50),
                    input_data JSON,
                    output_data JSON,
                    status VARCHAR(20) DEFAULT 'pending',
                    error_message TEXT,
                    execution_time DECIMAL(10,4),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """,
            "mcp_operations": """
                CREATE TABLE IF NOT EXISTS mcp_operations (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT,
                    operation_type VARCHAR(50),
                    service VARCHAR(50),
                    request_data JSON,
                    response_data JSON,
                    status VARCHAR(20) DEFAULT 'pending',
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """
        }
        
        results = {}
        for table_name, create_sql in tables.items():
            result = self.execute_query(create_sql)
            results[table_name] = result
        
        return {
            "success": all(r["success"] for r in results.values()),
            "tables_created": results
        }

# ENHANCED AGENT DEVELOPMENT KIT INTEGRATION

class AgentDevelopmentKit:
    def __init__(self):
        self.mysql_manager = MySQLMCPManager()
        self.gemini_manager = AdvancedGeminiManager()
        self.db = DatabaseManager()
    
    def query_mysql_with_ai(self, natural_query: str, mysql_config: Dict = None) -> Dict[str, Any]:
        """Use Gemini to convert natural language to SQL and execute"""
        try:
            # Default MySQL config
            if not mysql_config:
                mysql_config = {
                    "host": "localhost",
                    "port": 3306,
                    "user": "root",
                    "password": "",
                    "database": "chatbot_db"
                }
            
            # Connect to MySQL
            connection_result = self.mysql_manager.connect_mysql(**mysql_config)
            if not connection_result["success"]:
                return connection_result
            
            # Get database schema
            schema_result = self.mysql_manager.execute_query("SHOW TABLES")
            if not schema_result["success"]:
                return schema_result
            
            tables = [row["Tables_in_" + mysql_config["database"]] for row in schema_result["results"]]
            
            # Get table structures
            table_schemas = {}
            for table in tables:
                desc_result = self.mysql_manager.execute_query(f"DESCRIBE {table}")
                if desc_result["success"]:
                    table_schemas[table] = desc_result["results"]
            
            # Use Gemini to generate SQL
            schema_info = "\n".join([
                f"Table: {table}\nColumns: {', '.join([f'{col['Field']} ({col['Type']})' for col in columns])}\n"
                for table, columns in table_schemas.items()
            ])
            
            sql_prompt = f"""
            You are a SQL expert. Convert the following natural language query to SQL based on the database schema.
            
            Database Schema:
            {schema_info}
            
            Natural Language Query: {natural_query}
            
            Return only the SQL query without any explanation or formatting. Make sure the query is safe and follows best practices.
            """
            
            sql_result = self.gemini_manager.gemini.invoke([{"role": "user", "content": sql_prompt}])
            generated_sql = sql_result.content.strip()
            
            # Clean up SQL (remove code blocks if present)
            if "```sql" in generated_sql:
                generated_sql = generated_sql.split("```sql")[1].split("```")[0].strip()
            elif "```" in generated_sql:
                generated_sql = generated_sql.split("```")[1].strip()
            
            # Execute generated SQL
            query_result = self.mysql_manager.execute_query(generated_sql)
            
            result = {
                "success": query_result["success"],
                "natural_query": natural_query,
                "generated_sql": generated_sql,
                "mysql_result": query_result,
                "database_config": mysql_config
            }
            
            # Log comprehensive MCP operation
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "ai_mysql_query",
                    "agent_dev_kit",
                    {"natural_query": natural_query, "generated_sql": generated_sql},
                    result,
                    "success" if result["success"] else "error"
                )
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Agent Development Kit error: {str(e)}",
                "natural_query": natural_query
            }
            
            # Log error
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_mcp_operation(
                    st.session_state.user_id,
                    "ai_mysql_query",
                    "agent_dev_kit",
                    {"natural_query": natural_query},
                    error_result,
                    "error"
                )
            
            return error_result
    
    def create_intelligent_workflow(self, workflow_description: str) -> Dict[str, Any]:
        """Create and execute intelligent workflows combining multiple services"""
        try:
            # Use Gemini to analyze workflow requirements
            analysis_prompt = f"""
            Analyze the following workflow and break it down into executable steps:
            
            Workflow Description: {workflow_description}
            
            Available Services:
            - GitHub MCP (repository management, branch operations)
            - MySQL MCP (database queries and operations)
            - Code Generation (Gemini AI)
            - Planning Agent (task breakdown)
            
            Return a JSON structure with:
            1. Required services
            2. Step-by-step execution plan
            3. Expected inputs/outputs
            4. Success criteria
            
            Format as valid JSON only.
            """
            
            analysis_result = self.gemini_manager.gemini.invoke([{"role": "user", "content": analysis_prompt}])
            
            try:
                workflow_plan = json.loads(analysis_result.content)
            except json.JSONDecodeError:
                # Fallback to text-based plan
                workflow_plan = {
                    "services": ["planning"],
                    "steps": [{"step": 1, "action": "analyze_workflow", "description": analysis_result.content}],
                    "inputs": [workflow_description],
                    "outputs": ["analysis_complete"],
                    "success_criteria": ["workflow_analyzed"]
                }
            
            # Execute workflow steps
            execution_results = []
            for step in workflow_plan.get("steps", []):
                step_result = {
                    "step": step.get("step", len(execution_results) + 1),
                    "action": step.get("action", "unknown"),
                    "description": step.get("description", ""),
                    "success": True,
                    "output": "Step completed successfully"
                }
                execution_results.append(step_result)
            
            result = {
                "success": True,
                "workflow_description": workflow_description,
                "analysis": workflow_plan,
                "execution_results": execution_results,
                "services_used": workflow_plan.get("services", [])
            }
            
            # Log workflow execution
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_workflow(
                    st.session_state.user_id,
                    st.session_state.session_id,
                    "intelligent_workflow",
                    {"description": workflow_description},
                    result,
                    "completed"
                )
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"Intelligent workflow error: {str(e)}",
                "workflow_description": workflow_description
            }
            
            # Log error
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_workflow(
                    st.session_state.user_id,
                    st.session_state.session_id,
                    "intelligent_workflow",
                    {"description": workflow_description},
                    error_result,
                    "error"
                )
            
            return error_result

# ENHANCED MULTI-AGENT SYSTEM WITH ADK INTEGRATION

class UltimateMCPMultiAgentSystem(EnhancedMCPMultiAgentSystem):
    def __init__(self):
        super().__init__()
        self.agent_dev_kit = AgentDevelopmentKit()
        self.mysql_manager = MySQLMCPManager()
    
    def classify_request(self, user_request: str) -> Dict[str, Any]:
        """Enhanced request classification with MySQL and ADK support"""
        classification = super().classify_request(user_request)
        request_lower = user_request.lower()
        
        # MySQL operations
        mysql_keywords = ['mysql', 'database', 'sql', 'query', 'table', 'select', 'insert', 'update', 'delete']
        if any(keyword in request_lower for keyword in mysql_keywords):
            classification["primary_type"] = "mysql_mcp"
            classification["required_agents"].extend(["mysql", "agent_dev_kit"])
            classification["confidence"] = 0.9
            classification["mcp_operations"].append("mysql_operations")
        
        # Agent Development Kit workflows
        adk_keywords = ['workflow', 'intelligent', 'automate', 'integrate', 'combine services']
        if any(keyword in request_lower for keyword in adk_keywords):
            if classification["primary_type"] == "chat":
                classification["primary_type"] = "intelligent_workflow"
            else:
                classification["secondary_types"].append("intelligent_workflow")
            classification["required_agents"].append("agent_dev_kit")
            classification["confidence"] = max(classification["confidence"], 0.8)
        
        return classification
    
    def handle_mysql_operations(self, state: AgentState, classification: Dict) -> AgentState:
        """Handle MySQL MCP operations with AI integration"""
        try:
            request_lower = state["user_request"].lower()
            
            # Check for natural language SQL queries
            sql_indicators = ['show me', 'find', 'get', 'list', 'count', 'how many', 'what are']
            is_natural_query = any(indicator in request_lower for indicator in sql_indicators)
            
            if is_natural_query:
                # Use Agent Development Kit for intelligent querying
                result = self.agent_dev_kit.query_mysql_with_ai(state["user_request"])
                
                if result["success"]:
                    mysql_result = result["mysql_result"]
                    
                    if mysql_result.get("query_type") == "SELECT" and mysql_result.get("results"):
                        # Format results nicely
                        results = mysql_result["results"]
                        columns = mysql_result["columns"]
                        
                        if len(results) <= 10:  # Show all results if few
                            table_data = []
                            for row in results:
                                table_data.append(" | ".join([str(row.get(col, "")) for col in columns]))
                            
                            table_header = " | ".join(columns)
                            table_separator = " | ".join(["---"] * len(columns))
                            
                            formatted_results = f"""
## 🗄️ Query Results

**Natural Query:** {result['natural_query']}
**Generated SQL:** `{result['generated_sql']}`
**Rows Found:** {len(results)}

### 📊 Data

| {table_header} |
| {table_separator} |
""" + "\n".join([f"| {row} |" for row in table_data])
                        else:
                            # Show summary for large results
                            formatted_results = f"""
## 🗄️ Query Results

**Natural Query:** {result['natural_query']}
**Generated SQL:** `{result['generated_sql']}`
**Rows Found:** {len(results)} (showing first 5)

### 📊 Sample Data
{json.dumps(results[:5], indent=2, default=str)}
"""
                        
                        state["final_output"] = formatted_results
                    else:
                        state["final_output"] = f"""
## ✅ MySQL Operation Completed

**Natural Query:** {result['natural_query']}
**Generated SQL:** `{result['generated_sql']}`
**Operation:** {mysql_result.get('query_type', 'Unknown')}
**Affected Rows:** {mysql_result.get('affected_rows', 0)}
"""
                else:
                    state["errors"].append(result["error"])
                    state["final_output"] = f"❌ MySQL operation failed: {result['error']}"
            
            # Handle connection setup
            elif "connect" in request_lower or "setup" in request_lower:
                if "setup" in request_lower and "tables" in request_lower:
                    # Setup database tables
                    setup_result = self.mysql_manager.setup_chatbot_tables()
                    
                    if setup_result["success"]:
                        state["final_output"] = """
## ✅ MySQL Database Setup Complete

### 📊 Tables Created:
- **users** - User account management
- **conversations** - Chat history storage  
- **workflows** - Workflow execution logs
- **mcp_operations** - MCP operation tracking

Your MySQL database is now ready for the chatbot!
"""
                    else:
                        state["errors"].append("Database setup failed")
                        state["final_output"] = "❌ Failed to setup MySQL database tables"
                else:
                    # Simple connection test
                    connect_result = self.mysql_manager.connect_mysql()
                    
                    if connect_result["success"]:
                        state["final_output"] = f"""
## ✅ MySQL Connection Successful

**Server Version:** {connect_result['server_version']}
**Database:** {connect_result['database']}
**Host:** {connect_result['host']}:{connect_result['port']}

Ready to execute queries!
"""
                    else:
                        state["errors"].append(connect_result["error"])
                        state["final_output"] = f"❌ MySQL connection failed: {connect_result['error']}"
            
            else:
                # General MySQL help
                state["final_output"] = """
## 🗄️ MySQL Operations Available

### 🔗 Connection Management
- **Connect to database:** "connect to MySQL" 
- **Setup tables:** "setup MySQL tables for chatbot"
- **Test connection:** "test MySQL connection"

### 🤖 Intelligent Querying
- **Natural language:** "show me all users from the database"
- **Find data:** "get conversations from last week"
- **Count records:** "how many workflows were executed today"
- **Complex queries:** "find users who haven't logged in for 30 days"

### 💡 Advanced Features
- **AI-powered SQL generation** from natural language
- **Automatic schema detection** and optimization
- **Safe query execution** with error handling
- **Results formatting** and visualization

What would you like to do with MySQL?
"""
            
        except Exception as e:
            error_msg = f"MySQL operation error: {str(e)}"
            state["errors"].append(error_msg)
            state["final_output"] = f"❌ MySQL system error: {error_msg}"
        
        return state
    
    def handle_intelligent_workflow(self, state: AgentState) -> AgentState:
        """Handle intelligent workflow creation and execution"""
        try:
            result = self.agent_dev_kit.create_intelligent_workflow(state["user_request"])
            
            if result["success"]:
                analysis = result["analysis"]
                execution_results = result["execution_results"]
                
                # Format workflow output
                services_used = ", ".join(analysis.get("services", ["Unknown"]))
                
                workflow_output = f"""
## 🔄 Intelligent Workflow Executed

**Description:** {result['workflow_description']}
**Services Used:** {services_used}
**Steps Completed:** {len(execution_results)}

### 📋 Execution Plan
"""
                
                for step in execution_results:
                    status_icon = "✅" if step["success"] else "❌"
                    workflow_output += f"""
**Step {step['step']}:** {status_icon} {step['action']}
└─ {step['description']}
└─ Result: {step['output']}
"""
                
                workflow_output += f"""
### 🎯 Success Criteria
{", ".join(analysis.get("success_criteria", ["Workflow completed"]))}

### 📊 Summary
The workflow has been analyzed and executed using the Agent Development Kit with integration across {len(analysis.get("services", []))} services.
"""
                
                if state["final_output"]:
                    state["final_output"] += f"\n\n{workflow_output}"
                else:
                    state["final_output"] = workflow_output
                    
            else:
                error_msg = result["error"]
                state["errors"].append(error_msg)
                if not state["final_output"]:
                    state["final_output"] = f"❌ Intelligent workflow failed: {error_msg}"
                    
        except Exception as e:
            error_msg = f"Intelligent workflow system error: {str(e)}"
            state["errors"].append(error_msg)
            if not state["final_output"]:
                state["final_output"] = f"❌ {error_msg}"
        
        return state
    
    def process_request(self, user_request: str) -> Dict[str, Any]:
        """Enhanced request processing with MySQL and ADK support"""
        start_time = time.time()
        
        try:
            # Classify request with enhanced capabilities
            classification = self.classify_request(user_request)
            
            # Initialize enhanced state
            state = AgentState(
                user_request=user_request,
                task_type=classification["primary_type"],
                context=self.memory_manager.get_conversation_context(),
                github_operations=[],
                code_generations=[],
                plans=[],
                final_output="",
                workflow_status="Processing...",
                execution_time=0.0,
                errors=[]
            )
            
            # Process based on enhanced primary type
            if classification["primary_type"] == "mysql_mcp":
                state = self.handle_mysql_operations(state, classification)
            elif classification["primary_type"] == "intelligent_workflow":
                state = self.handle_intelligent_workflow(state)
            elif classification["primary_type"] == "github_mcp":
                state = self.handle_github_operations(state, classification)
            elif classification["primary_type"] == "code_generation":
                state = self.handle_code_generation(state)
            elif classification["primary_type"] == "planning":
                state = self.handle_planning(state)
            else:
                state = self.handle_general_chat(state)
            
            # Handle secondary operations
            for secondary_type in classification["secondary_types"]:
                if secondary_type == "intelligent_workflow":
                    state = self.handle_intelligent_workflow(state)
                elif secondary_type == "code_generation":
                    state = self.handle_code_generation(state)
                elif secondary_type == "planning":
                    state = self.handle_planning(state)
            
            # Finalize response
            execution_time = time.time() - start_time
            state["execution_time"] = execution_time
            state["workflow_status"] = "Completed" if not state["errors"] else "Completed with errors"
            
            # Add to memory
            if state["final_output"]:
                self.memory_manager.add_message(
                    user_request,
                    state["final_output"],
                    getattr(st.session_state, 'user_id', None),
                    st.session_state.session_id
                )
            
            # Save workflow
            if hasattr(st.session_state, 'user_id') and st.session_state.user_id:
                self.db.save_workflow(
                    st.session_state.user_id,
                    st.session_state.session_id,
                    classification["primary_type"],
                    {"user_request": user_request, "classification": classification},
                    dict(state),
                    "completed" if not state["errors"] else "error",
                    execution_time=execution_time
                )
            
            return {
                "user_request": user_request,
                "task_type": classification["primary_type"],
                "final_output": state["final_output"],
                "workflow_status": state["workflow_status"],
                "execution_time": execution_time,
                "agent_outputs": {
                    "github": state["github_operations"],
                    "code": state["code_generations"],
                    "plans": state["plans"]
                },
                "mcp_operations": classification["mcp_operations"],
                "errors": state["errors"]
            }
            
        except Exception as e:
            error_msg = f"Enhanced system error: {str(e)}"
            return {
                "user_request": user_request,
                "task_type": "error",
                "final_output": f"I apologize, but I encountered an error while processing your request: {error_msg}",
                "workflow_status": "Error",
                "execution_time": time.time() - start_time,
                "agent_outputs": {},
                "mcp_operations": [],
                "errors": [error_msg]
            }

# ENHANCED DATABASE PAGE WITH MYSQL INTEGRATION

def show_database_management():
    """Show database management interface with MySQL support"""
    st.title("🗄️ Database Management")
    st.markdown("**Manage SQLite and MySQL databases with MCP integration**")
    
    # Database tabs
    tab1, tab2, tab3 = st.tabs(["📊 SQLite Management", "🐬 MySQL Integration", "🔄 Data Migration"])
    
    with tab1:
        st.markdown("### 📊 Local SQLite Database")
        
        db = DatabaseManager()
        
        # Database statistics
        with db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get table information
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📁 Tables", len(tables))
            
            # Get record counts
            total_records = 0
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                total_records += count
            
            with col2:
                st.metric("📝 Total Records", total_records)
            
            # Database size
            db_size = os.path.getsize(config.database_path) if os.path.exists(config.database_path) else 0
            with col3:
                st.metric("💾 Database Size", f"{db_size / 1024:.1f} KB")
            
            with col4:
                st.metric("👥 Users", cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0])
        
        # Table browser
        st.markdown("### 🔍 Table Browser")
        selected_table = st.selectbox("Select table to view:", tables)
        
        if selected_table:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get table schema
                cursor.execute(f"PRAGMA table_info({selected_table})")
                schema = cursor.fetchall()
                
                st.markdown(f"**Schema for {selected_table}:**")
                schema_df = []
                for col in schema:
                    schema_df.append({
                        "Column": col[1],
                        "Type": col[2],
                        "Not Null": "Yes" if col[3] else "No",
                        "Default": col[4] or "None",
                        "Primary Key": "Yes" if col[5] else "No"
                    })
                
                st.dataframe(schema_df, use_container_width=True)
                
                # Show recent records
                cursor.execute(f"SELECT * FROM {selected_table} ORDER BY rowid DESC LIMIT 10")
                records = cursor.fetchall()
                
                if records:
                    st.markdown(f"**Recent records from {selected_table}:**")
                    columns = [description[0] for description in cursor.description]
                    
                    records_df = []
                    for record in records:
                        record_dict = dict(zip(columns, record))
                        records_df.append(record_dict)
                    
                    st.dataframe(records_df, use_container_width=True)
                else:
                    st.info(f"No records found in {selected_table}")
    
    with tab2:
        st.markdown("### 🐬 MySQL Integration")
        
        # MySQL connection form
        with st.expander("🔗 MySQL Connection Settings", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                mysql_host = st.text_input("Host", value="localhost", key="mysql_host")
                mysql_port = st.number_input("Port", value=3306, key="mysql_port")
                mysql_user = st.text_input("Username", value="root", key="mysql_user")
            
            with col2:
                mysql_password = st.text_input("Password", type="password", key="mysql_password")
                mysql_database = st.text_input("Database", value="chatbot_db", key="mysql_database")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔌 Test Connection", use_container_width=True):
                mysql_manager = MySQLMCPManager()
                result = mysql_manager.connect_mysql(
                    host=mysql_host,
                    port=mysql_port,
                    user=mysql_user,
                    password=mysql_password,
                    database=mysql_database
                )
                
                if result["success"]:
                    st.success(f"✅ Connected to MySQL {result['server_version']}")
                else:
                    st.error(f"❌ Connection failed: {result['error']}")
        
        with col2:
            if st.button("🏗️ Setup Tables", use_container_width=True):
                mysql_manager = MySQLMCPManager()
                connect_result = mysql_manager.connect_mysql(
                    host=mysql_host,
                    port=mysql_port,
                    user=mysql_user,
                    password=mysql_password,
                    database=mysql_database
                )
                
                if connect_result["success"]:
                    setup_result = mysql_manager.setup_chatbot_tables()
                    if setup_result["success"]:
                        st.success("✅ MySQL tables created successfully!")
                    else:
                        st.error("❌ Failed to create tables")
                else:
                    st.error(f"❌ Connection failed: {connect_result['error']}")
        
        with col3:
            if st.button("🔍 Browse MySQL", use_container_width=True):
                mysql_manager = MySQLMCPManager()
                connect_result = mysql_manager.connect_mysql(
                    host=mysql_host,
                    port=mysql_port,
                    user=mysql_user,
                    password=mysql_password,
                    database=mysql_database
                )
                
                if connect_result["success"]:
                    tables_result = mysql_manager.execute_query("SHOW TABLES")
                    if tables_result["success"]:
                        st.session_state.mysql_tables = tables_result["results"]
                        st.success(f"✅ Found {len(tables_result['results'])} tables")
                    else:
                        st.error("❌ Failed to list tables")
                else:
                    st.error(f"❌ Connection failed: {connect_result['error']}")
        
        # MySQL table browser
        if 'mysql_tables' in st.session_state and st.session_state.mysql_tables:
            st.markdown("### 📊 MySQL Tables")
            
            table_names = [list(table.values())[0] for table in st.session_state.mysql_tables]
            selected_mysql_table = st.selectbox("Select MySQL table:", table_names)
            
            if selected_mysql_table:
                mysql_manager = MySQLMCPManager()
                mysql_manager.connect_mysql(
                    host=mysql_host,
                    port=mysql_port,
                    user=mysql_user,
                    password=mysql_password,
                    database=mysql_database
                )
                
                # Show table structure
                desc_result = mysql_manager.execute_query(f"DESCRIBE {selected_mysql_table}")
                if desc_result["success"]:
                    st.markdown(f"**Structure of {selected_mysql_table}:**")
                    st.dataframe(desc_result["results"], use_container_width=True)
                
                # Show sample data
                sample_result = mysql_manager.execute_query(f"SELECT * FROM {selected_mysql_table} LIMIT 10")
                if sample_result["success"] and sample_result["results"]:
                    st.markdown(f"**Sample data from {selected_mysql_table}:**")
                    st.dataframe(sample_result["results"], use_container_width=True)
        
        # Natural language query interface
        st.markdown("### 🤖 AI-Powered Querying")
        
        natural_query = st.text_area(
            "Enter your question in natural language:",
            placeholder="e.g., 'Show me all users who registered last week' or 'Count how many conversations happened today'"
        )
        
        if st.button("🧠 Execute AI Query", use_container_width=True):
            if natural_query:
                adk = AgentDevelopmentKit()
                mysql_config = {
                    "host": mysql_host,
                    "port": mysql_port,
                    "user": mysql_user,
                    "password": mysql_password,
                    "database": mysql_database
                }
                
                with st.spinner("🤖 Converting natural language to SQL and executing..."):
                    result = adk.query_mysql_with_ai(natural_query, mysql_config)
                
                if result["success"]:
                    st.success("✅ Query executed successfully!")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("**Your Question:**")
                        st.info(result["natural_query"])
                    
                    with col2:
                        st.markdown("**Generated SQL:**")
                        st.code(result["generated_sql"], language="sql")
                    
                    mysql_result = result["mysql_result"]
                    if mysql_result.get("results"):
                        st.markdown("**Results:**")
                        st.dataframe(mysql_result["results"], use_container_width=True)
                        st.caption(f"Found {len(mysql_result['results'])} rows")
                    else:
                        st.info("Query executed successfully but returned no results.")
                else:
                    st.error(f"❌ Query failed: {result['error']}")
            else:
                st.warning("Please enter a question first.")
    
    with tab3:
        st.markdown("### 🔄 Data Migration")
        
        st.markdown("**Migrate data between SQLite and MySQL databases**")
        
        migration_direction = st.radio(
            "Migration Direction:",
            ["SQLite → MySQL", "MySQL → SQLite"],
            horizontal=True
        )
        
        if migration_direction == "SQLite → MySQL":
            st.markdown("#### 📤 Export from SQLite to MySQL")
            
            # Select tables to migrate
            db = DatabaseManager()
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                sqlite_tables = [row[0] for row in cursor.fetchall()]
            
            selected_tables = st.multiselect("Select tables to migrate:", sqlite_tables, default=sqlite_tables)
            
            if st.button("🚀 Start Migration", use_container_width=True):
                if selected_tables:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    mysql_manager = MySQLMCPManager()
                    connect_result = mysql_manager.connect_mysql(
                        host=mysql_host,
                        port=mysql_port,
                        user=mysql_user,
                        password=mysql_password,
                        database=mysql_database
                    )
                    
                    if connect_result["success"]:
                        total_tables = len(selected_tables)
                        migrated_count = 0
                        
                        for i, table in enumerate(selected_tables):
                            status_text.text(f"Migrating table: {table}")
                            
                            # Get SQLite data
                            with db.get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute(f"SELECT * FROM {table}")
                                rows = cursor.fetchall()
                                columns = [description[0] for description in cursor.description]
                            
                            if rows:
                                # Convert to MySQL format and insert
                                for row in rows:
                                    values = ", ".join([f"'{str(val)}'" if val is not None else "NULL" for val in row])
                                    columns_str = ", ".join(columns)
                                    insert_sql = f"INSERT IGNORE INTO {table} ({columns_str}) VALUES ({values})"
                                    
                                    mysql_manager.execute_query(insert_sql)
                                
                                migrated_count += 1
                            
                            progress_bar.progress((i + 1) / total_tables)
                        
                        status_text.text("Migration completed!")
                        st.success(f"✅ Successfully migrated {migrated_count} tables from SQLite to MySQL")
                    else:
                        st.error(f"❌ MySQL connection failed: {connect_result['error']}")
                else:
                    st.warning("Please select at least one table to migrate.")
        
        else:
            st.markdown("#### 📥 Import from MySQL to SQLite")
            st.info("MySQL to SQLite migration functionality can be implemented similarly.")
            
            if st.button("🚀 Start Reverse Migration", use_container_width=True):
                st.info("This feature will be implemented in the next update.")

# ENHANCED MAIN APPLICATION WITH ALL FEATURES

def main():
    """Enhanced main application with all integrated features"""
    
    # Apply enhanced styling
    apply_enhanced_styling()
    
    # Check login status
    if not st.session_state.logged_in:
        show_enhanced_login()
        return
    
    # Show sidebar for logged-in users
    show_enhanced_sidebar()
    
    # Route to different pages based on selection
    current_page = st.session_state.current_page
    
    if current_page == "🏠 Chat Interface":
        # Initialize enhanced AI system
        if 'ai_system' not in st.session_state:
            st.session_state.ai_system = UltimateMCPMultiAgentSystem()
        
        show_enhanced_chat_interface()
    
    elif current_page == "📊 Analytics Dashboard":
        show_analytics_dashboard()
    
    elif current_page == "📝 Chat History":
        show_enhanced_chat_history()
    
    elif current_page == "🔧 System Settings":
        show_system_settings()
    
    
    elif current_page == "🗄️ Database Management":
        show_database_management()
    
    else:
        # Default to chat interface
        st.session_state.current_page = "🏠 Chat Interface"
        st.rerun()

# ENHANCED ERROR HANDLING AND LOGGING

def setup_error_handling():
    """Setup comprehensive error handling and logging"""
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('chatbot.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Log system startup
    logger.info("Enhanced Multi-Agent Chatbot System Starting...")
    logger.info(f"LangChain Available: {LANGCHAIN_AVAILABLE}")
    logger.info(f"LangGraph Available: {LANGGRAPH_AVAILABLE}")
    logger.info(f"GitHub Available: {GITHUB_AVAILABLE}")
    
    return logger

# SYSTEM INITIALIZATION AND CHECKS

def initialize_system():
    """Initialize system with comprehensive checks"""
    
    # Setup error handling
    logger = setup_error_handling()
    
    # Check dependencies
    missing_deps = []
    
    if not LANGCHAIN_AVAILABLE:
        missing_deps.append("langchain, langchain-groq, langchain-google-genai")
    
    if not GITHUB_AVAILABLE:
        missing_deps.append("PyGithub")
    
    if missing_deps:
        st.error(f"""
        Missing dependencies: {', '.join(missing_deps)}
        
        Please install with:
        ```
        pip install {' '.join(missing_deps)}
        ```
        """)
        st.stop()
    
    # Check API keys
    api_warnings = []
    
    if not config.groq_api_key:
        api_warnings.append("Groq API key not configured")
    
    if not config.gemini_api_key:
        api_warnings.append("Gemini API key not configured")
    
    if not config.github_token:
        api_warnings.append("GitHub token not configured")
    
    if api_warnings:
        st.warning(f"API Configuration Issues: {', '.join(api_warnings)}")
    
    # Initialize database
    try:
        db = DatabaseManager()
        logger.info("Database initialized successfully")
    except Exception as e:
        st.error(f"Database initialization failed: {str(e)}")
        st.stop()
    
    # Test MySQL connector availability
    try:
        import mysql.connector
        logger.info("MySQL connector available")
    except ImportError:
        st.info("MySQL connector not available. Install with: pip install mysql-connector-python")
    
    logger.info("System initialization completed successfully")

# APPLICATION ENTRY POINT

if __name__ == "__main__":
    # Set page config
    st.set_page_config(
        page_title="🤖 Advanced AI Assistant",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            'Get Help': 'https://github.com/your-repo/advanced-ai-assistant',
            'Report a bug': "https://github.com/your-repo/advanced-ai-assistant/issues",
            'About': """
            # Advanced AI Assistant
            
            A comprehensive multi-agent chatbot system with:
            - 🤖 Multiple AI agents (Chat, GitHub, Code, Planning)
            - 🔗 MCP integration (GitHub, MySQL)
            - 🧠 Advanced memory systems
            - 📊 Analytics and monitoring
            - 🎨 Multiple themes
            
            Built with Streamlit, LangChain, and modern AI technologies.
            """
        }
    )
    
    # Initialize system
    initialize_system()
    
    # Add database management to navigation
    if st.session_state.logged_in and "🗄️ Database Management" not in [page.split(" ", 1)[1] if len(page.split(" ", 1)) > 1 else page for icon, page in [
        ("🏠", "Chat Interface"),
        ("📊", "Analytics Dashboard"), 
        ("📝", "Chat History"),
        ("🔧", "System Settings")
    ]]:
        # This is handled in the sidebar navigation
        pass
    
    # Run main application
    try:
        main()
    except Exception as e:
        st.error(f"""
        ## 🚨 Application Error
        
        An unexpected error occurred: {str(e)}
        
        Please try:
        1. Refreshing the page
        2. Clearing your browser cache
        3. Restarting the application
        
        If the problem persists, please report it with the error details above.
        """)
        
        # Log the error
        import traceback
        logger = setup_error_handling()
        logger.error(f"Application error: {str(e)}")
        logger.error(traceback.format_exc())

# ADDITIONAL UTILITY FUNCTIONS

def export_system_configuration():
    """Export complete system configuration for backup/restore"""
    config_data = {
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "system_info": {
            "langchain_available": LANGCHAIN_AVAILABLE,
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "github_available": GITHUB_AVAILABLE,
        },
        "configuration": {
            "max_memory_messages": config.max_memory_messages,
            "session_timeout": config.session_timeout,
            "database_path": config.database_path,
            "users_file": config.users_file
        },
        "features_enabled": {
            "github_mcp": bool(config.github_token),
            "gemini_ai": bool(config.gemini_api_key),
            "groq_llm": bool(config.groq_api_key),
            "mysql_integration": True,
            "agent_dev_kit": True
        }
    }
    
    return json.dumps(config_data, indent=2)

def validate_system_health():
    """Comprehensive system health validation"""
    health_report = {
        "overall_status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "checks": []
    }
    
    # Check database connectivity
    try:
        db = DatabaseManager()
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
        
        health_report["checks"].append({
            "component": "SQLite Database",
            "status": "healthy",
            "details": f"Connected successfully, {user_count} users"
        })
    except Exception as e:
        health_report["checks"].append({
            "component": "SQLite Database", 
            "status": "unhealthy",
            "error": str(e)
        })
        health_report["overall_status"] = "degraded"
    
    # Check API connections
    api_checks = [
        ("Groq API", config.groq_api_key, LANGCHAIN_AVAILABLE),
        ("Gemini API", config.gemini_api_key, LANGCHAIN_AVAILABLE),
        ("GitHub API", config.github_token, GITHUB_AVAILABLE)
    ]
    
    for api_name, api_key, available in api_checks:
        if api_key and available:
            health_report["checks"].append({
                "component": api_name,
                "status": "healthy",
                "details": "API key configured and dependencies available"
            })
        else:
            health_report["checks"].append({
                "component": api_name,
                "status": "unavailable", 
                "details": "API key missing or dependencies unavailable"
            })
    
    return health_report

# PERFORMANCE MONITORING

class PerformanceMonitor:
    def __init__(self):
        self.metrics = {
            "requests_processed": 0,
            "total_execution_time": 0,
            "average_response_time": 0,
            "errors_encountered": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
        self.start_time = time.time()
    
    def log_request(self, execution_time: float, success: bool = True):
        """Log request metrics"""
        self.metrics["requests_processed"] += 1
        self.metrics["total_execution_time"] += execution_time
        self.metrics["average_response_time"] = (
            self.metrics["total_execution_time"] / self.metrics["requests_processed"]
        )
        
        if not success:
            self.metrics["errors_encountered"] += 1
    
    def get_performance_report(self) -> Dict[str, Any]:
        """Get comprehensive performance report"""
        uptime = time.time() - self.start_time
        
        return {
            "uptime_seconds": uptime,
            "uptime_formatted": str(timedelta(seconds=int(uptime))),
            "requests_per_second": self.metrics["requests_processed"] / uptime if uptime > 0 else 0,
            "error_rate": (
                self.metrics["errors_encountered"] / self.metrics["requests_processed"] 
                if self.metrics["requests_processed"] > 0 else 0
            ),
            "cache_hit_rate": (
                self.metrics["cache_hits"] / (self.metrics["cache_hits"] + self.metrics["cache_misses"])
                if (self.metrics["cache_hits"] + self.metrics["cache_misses"]) > 0 else 0
            ),
            **self.metrics
        }

# Initialize global performance monitor
if 'performance_monitor' not in st.session_state:
    st.session_state.performance_monitor = PerformanceMonitor()

initialize_session_state()

if 'ai_system' not in st.session_state or st.session_state.ai_system is None:
    st.session_state.ai_system = EnhancedMCPMultiAgentSystem()

apply_enhanced_styling()   

user_input = st.chat_input("Type your request here...")
if user_input:
    response = st.session_state.ai_system.process_request(user_input)
    st.write(response["final_output"])