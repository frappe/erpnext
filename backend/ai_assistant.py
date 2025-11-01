import os
from anthropic import Anthropic
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

class ERIKAIAssistant:
    """
    ERIK AI Assistant powered by Claude
    Provides intelligent assistance for ERP tasks, natural language queries, and business insights
    """
    
    def __init__(self):
        self.model = "claude-sonnet-4-5"  # Balanced performance and speed
        self._client = None  # Lazy initialization
        
    def _get_client(self):
        """Lazy initialization of Anthropic client with proper error handling"""
        if self._client is None:
            api_key = os.getenv("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
            base_url = os.getenv("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
            
            if not api_key:
                raise ValueError(
                    "AI_INTEGRATIONS_ANTHROPIC_API_KEY not configured. "
                    "Please set up the Anthropic integration in Replit."
                )
            
            try:
                if base_url:
                    self._client = Anthropic(api_key=api_key, base_url=base_url)
                else:
                    self._client = Anthropic(api_key=api_key)
            except Exception as e:
                raise RuntimeError(f"Failed to initialize Anthropic client: {str(e)}")
                
        return self._client
        
    def get_system_prompt(self, user_context: Optional[Dict[str, Any]] = None) -> str:
        """Generate context-aware system prompt for ERIK"""
        base_prompt = """You are ERIK (Enterprise Resource & Intelligence Kernel), an AI assistant integrated into a comprehensive ERP system designed for Zambian businesses.

Your capabilities include:
- Analyzing financial data (P&L, Balance Sheet, Cash Flow)
- Interpreting HR metrics (headcount, turnover, payroll costs)
- Providing insights on inventory, sales, and procurement
- Explaining Zambian statutory compliance (ZRA, NAPSA, NHIMA, PAYE)
- Generating business recommendations based on company data
- Helping users navigate the ERP system

Important guidelines:
1. Always verify critical financial calculations and recommendations
2. Remind users to consult qualified professionals for major business decisions
3. Clarify when you're providing analysis vs. professional advice
4. Use ZMW (Zambian Kwacha) as the default currency
5. Consider Zambian business regulations and tax laws

Current date: {date}
"""
        
        if user_context:
            context_info = f"\n\nUser Context:\n- Company: {user_context.get('company_name', 'Unknown')}\n"
            context_info += f"- User: {user_context.get('user_name', 'Unknown')}\n"
            context_info += f"- Role: {user_context.get('role', 'User')}\n"
            base_prompt += context_info
            
        return base_prompt.format(date=datetime.now().strftime("%B %d, %Y"))
    
    async def chat(
        self, 
        message: str, 
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_context: Optional[Dict[str, Any]] = None,
        include_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Send a message to ERIK AI Assistant
        
        Args:
            message: User's message/question
            conversation_history: Previous messages in format [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            user_context: User and company information
            include_data: Additional data to include (financial reports, employee data, etc.)
        
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Build messages array
            messages = conversation_history or []
            
            # Add data context if provided
            if include_data:
                data_context = "\n\nRelevant Data:\n" + json.dumps(include_data, indent=2)
                message = message + data_context
            
            # Add current message
            messages.append({
                "role": "user",
                "content": message
            })
            
            # Call Claude API with lazy client initialization
            client = self._get_client()
            response = client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=self.get_system_prompt(user_context),
                messages=messages
            )
            
            # Extract response text
            assistant_message = response.content[0].text
            
            # Add disclaimer for financial/legal advice
            if any(keyword in message.lower() for keyword in ['tax', 'legal', 'compliance', 'audit', 'should i', 'recommend']):
                assistant_message += "\n\n⚠️ **Disclaimer**: This is AI-generated guidance. Please verify critical decisions with qualified professionals (accountants, lawyers, tax advisors)."
            
            return {
                "success": True,
                "response": assistant_message,
                "model": self.model,
                "tokens_used": response.usage.input_tokens + response.usage.output_tokens,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response": "I apologize, but I encountered an error processing your request. Please try again or contact support if the issue persists."
            }
    
    async def analyze_financial_report(
        self, 
        report_type: str, 
        data: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze financial reports and provide insights
        
        Args:
            report_type: Type of report (profit_loss, balance_sheet, cash_flow)
            data: Financial data to analyze
            user_context: User and company information
        
        Returns:
            AI-generated analysis and insights
        """
        prompts = {
            "profit_loss": "Analyze this Profit & Loss statement and provide key insights on revenue, expenses, profitability trends, and recommendations.",
            "balance_sheet": "Analyze this Balance Sheet and provide insights on financial position, liquidity, solvency, and asset management.",
            "cash_flow": "Analyze this Cash Flow statement and provide insights on operating, investing, and financing activities."
        }
        
        prompt = prompts.get(report_type, "Analyze this financial report and provide insights.")
        
        return await self.chat(
            message=prompt,
            user_context=user_context,
            include_data=data
        )
    
    async def predict_demand(
        self,
        product_data: Dict[str, Any],
        historical_sales: List[Dict[str, Any]],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Predict product demand based on historical sales data
        """
        message = f"""Based on the historical sales data for {product_data.get('name', 'this product')}, 
provide a demand forecast for the next 3 months. Consider seasonal trends, growth patterns, and any anomalies."""
        
        return await self.chat(
            message=message,
            user_context=user_context,
            include_data={"product": product_data, "sales_history": historical_sales}
        )
    
    async def explain_statutory_compliance(
        self,
        compliance_type: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Explain Zambian statutory compliance requirements
        """
        prompts = {
            "paye": "Explain Zambian PAYE (Pay As You Earn) tax requirements, calculation methods, and filing deadlines.",
            "napsa": "Explain NAPSA (National Pension Scheme Authority) contribution requirements, rates, and compliance.",
            "nhima": "Explain NHIMA (National Health Insurance Management Authority) contribution requirements and compliance.",
            "vat": "Explain VAT requirements in Zambia, including registration thresholds, rates, and Smart Invoice compliance.",
            "sdl": "Explain Skills Development Levy (SDL) requirements in Zambia."
        }
        
        prompt = prompts.get(compliance_type.lower(), f"Explain {compliance_type} compliance requirements in Zambia.")
        
        return await self.chat(
            message=prompt,
            user_context=user_context
        )
    
    async def generate_summary(
        self,
        data_type: str,
        data: Dict[str, Any],
        user_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate executive summaries for management
        """
        message = f"Generate a concise executive summary of this {data_type} data, highlighting key metrics and actionable insights."
        
        return await self.chat(
            message=message,
            user_context=user_context,
            include_data=data
        )

# Global instance
ai_assistant = ERIKAIAssistant()
