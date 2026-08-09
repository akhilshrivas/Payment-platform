import json
import logging
from apps.ai.models import AIConversation, AIMessage
from apps.ai.services.llm_provider import AIProvider
from apps.ai.services.tool_service import ToolService, TOOLS_SCHEMA
from apps.ai.prompts.system_prompt import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class AssistantService:
    def __init__(self, user):
        self.user = user
        self.provider = AIProvider()

    def _execute_tool(self, name, arguments):
        """Execute a tool safely scoped to the authenticated user."""
        try:
            kwargs = json.loads(arguments) if isinstance(arguments, str) else arguments
            func = getattr(ToolService, name, None)
            if not func:
                return {"error": f"Tool {name} not found"}
            
            # Critical Security Rule: Always pass the authenticated user to the tool.
            # Never trust a user_id from the LLM.
            return func(user=self.user, **kwargs)
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {"error": "Failed to execute tool."}

    def process_message(self, conversation, message_content):
        # 1. Save user message
        AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.RoleChoices.USER,
            content=message_content
        )

        # 2. Prepare conversation history for LLM
        history = AIMessage.objects.filter(conversation=conversation).order_by("created_at")
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history:
            messages.append({"role": msg.role, "content": msg.content})

        # 3. Call LLM
        response = self.provider.generate_response(messages, tools=TOOLS_SCHEMA)

        # Handle LLM API error
        if isinstance(response, dict) and "error" in response:
            error_msg = response["error"]
            AIMessage.objects.create(
                conversation=conversation,
                role=AIMessage.RoleChoices.ASSISTANT,
                content=error_msg
            )
            return error_msg

        # 4. Handle Tool Calls if any
        if response.get("tool_calls"):
            # The LLM wants to call one or more tools
            messages.append(response) # Append the assistant's tool call message
            
            for tool_call in response["tool_calls"]:
                tool_name = tool_call["function"]["name"]
                tool_args = tool_call["function"]["arguments"]
                logger.info(f"LLM invoked tool: {tool_name}")
                
                tool_result = self._execute_tool(tool_name, tool_args)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": tool_name,
                    "content": json.dumps(tool_result)
                })

            # Call LLM again with tool results
            response = self.provider.generate_response(messages, tools=TOOLS_SCHEMA)

        # 5. Save assistant response
        if isinstance(response, dict) and "error" in response:
            final_content = response["error"]
        else:
            final_content = response.get("content", "I am unable to process that request right now.")

        AIMessage.objects.create(
            conversation=conversation,
            role=AIMessage.RoleChoices.ASSISTANT,
            content=final_content
        )

        return final_content
