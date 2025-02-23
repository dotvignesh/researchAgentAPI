from fastapi import FastAPI, HTTPException
from smolagents import CodeAgent, DuckDuckGoSearchTool, ToolCallingAgent
from smolagents.models import OpenAIServerModel
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import openai
import json
from pyngrok import ngrok
import uvicorn
import threading

# Load environment variables
load_dotenv()

from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI app
app = FastAPI(title="Market Research and Presentation API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this for production
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

# Define request model
class ResearchRequest(BaseModel):
    prompt: str

class EditRequest(BaseModel):
    html_input: str
    prompt: str

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_market_research_agent():
    model = OpenAIServerModel(
        model_id="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    web_tools = [DuckDuckGoSearchTool()]

    web_search_agent = ToolCallingAgent(
        model=model,
        tools=web_tools,
        max_steps=20,
        verbosity_level=2,
        planning_interval=4,
        name="search_agent",
        description="""A team member that will search the internet to answer your question.
    Ask him for all your questions that require browsing the web.
    Provide him as much context as possible, in particular if you need to search on a specific timeframe!
    And don't hesitate to provide him with a complex search task, like finding a difference between two webpages.
    Your request must be a real sentence, not a google search! Like "Find me this information (...)" rather than a few keywords.
    """,
        provide_run_summary=True,
    )
    
    manager_agent = CodeAgent(
        model=model,
        tools=web_tools,
        verbosity_level=2,
        managed_agents=[web_search_agent],
        planning_interval=4,
        additional_authorized_imports=["requests", "os", "json"]
    )
    return manager_agent

def create_markdown_agent():
    model = OpenAIServerModel(
        model_id="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    return CodeAgent(
        model=model,
        tools=[],
        verbosity_level=0,
        additional_authorized_imports=["json"]
    )

# Global agent instances
market_research_agent = create_market_research_agent()
markdown_agent = create_markdown_agent()

def presentation_code_agent(prompt: str) -> str:
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return response.choices[0].message.content.strip()

import traceback  # For detailed error logging

@app.post("/research/presentation")
async def conduct_research_and_present(request: ResearchRequest):
    try:
        research_prompt = f"""
        You are a world-class market research consultant with credentials from top institutions such as INSEAD and Harvard. 
        Your task is to perform a rigorous, data-driven analysis solely based on real-time research conducted using the available web tool. 
        You must ALWAYS and without exception use the web tool to retrieve *only factual, up-to-date information* from highly credible online sources.
        Do not rely on any pre-existing internal knowledge or unverified content—every data point in your analysis must be backed by a web-sourced reference (include source URLs).

        It is paramount that you provide a correct answer.
        Give it all you can: I know for a fact that you have access to all the relevant tools to solve it and find the correct answer (the answer does exist). Failure or 'I cannot answer' or 'None found' will not be tolerated, success will be rewarded.
        Run verification steps if that's needed, you must make sure you find the correct answer!
        Here is the task:

        Your analysis must include the following baseline components:

        1. **Strategic Research Framework (MANDATORY Web Tool Usage)**:
        - Clearly define the primary market research objectives, including identification of key industry trends, competitive dynamics, and market size.
        - Specify precise data requirements (e.g., relevant industry reports, statistical data).
        - Prioritize information exclusively from authoritative, reputable sources.
        - For every piece of data, ensure you include a reference to its online source (i.e., source URL) (after using the web tool).

        2. **Data Acquisition (MANDATORY Web Tool Usage)**:
        - Execute web searches using the web tool to gather the most recent (within the last 1-2 years) and reliable data.
        - Prioritize information exclusively from authoritative, reputable sources.
        - For every piece of data, ensure you include a reference to its online source (i.e., source URL) (after using the web tool).

        3. **Critical Data Analysis**:
        - Synthesize the collected data to extract significant trends, opportunities, risks, and potential market gaps.
        - Provide an incisive, evidence-based analysis that informs strategic decision-making, using only the data acquired via the web tool.

        If the user's prompt does not specify a particular industry, refrain from conducting an analysis.

        User prompt: {request.prompt}

        **Structured Deliverable**:
        - Prepare a JSON object that dynamically reflects the needs of the specific query. At a minimum, include:
            - "research_objectives": A list of clearly stated objectives.
            - "data_collected": A dictionary summarizing key findings with source URLs. (after using the web tool)
            - "analysis": A concise, fact-based summary of insights.
            - "recommendations": A list of actionable, data-driven strategic recommendations.
        - If the query or topic warrants additional insights or sections, dynamically include extra fields that best capture the full scope of your analysis.

        Return only the structured JSON response, STRICTLY ONLY AFTER YOU HAVE COMPLETED ALL YOUR ANALYSIS, with no additional commentary or explanation. Do not redact any data anywhere in the final output. The user needs to know your complete analysis always.
        """


        
        print("-------STARTING RESEARCH---------")
        
        # Run the research agent
        analysis = market_research_agent.run(research_prompt)

        # Generate markdown summary
        markdown_prompt = f"""
        You are a presentation generator. Given the semi-structured market research analysis data below, create a clean, concise Markdown summary of the analysis. Focus on clarity and professionalism. 
        Include every piece of information provided to you.
        Do not change or add any extra information to you more than what's given to you.

        Analysis Data:
        {analysis}

        Return only the Markdown string, no additional text.
        """

        print("-------GENERATING MARKDOWN---------")
        
        markdown_output = markdown_agent.run(markdown_prompt)

        print("-------MARKDOWN DONE---------")
        
        # Generate Reveal.js code
        print("-------GENERATING REVEAL.JS PRESENTATION---------")
        presentation_prompt = f"""
        You are a coding assistant tasked with generating a Reveal.js presentation based on a market research analysis. 
        Given the analysis below, create a complete HTML file with Reveal.js setup and slides. Include only the necessary content from the analysis, create as many slides as required.

        Use the Reveal.js CDN (https://cdn.jsdelivr.net/npm/reveal.js@4.6.0/dist/). 
        Use clean and minimalistic styling - it should look professional like how Apple's PPTs would look. 
        But don't make it look very boring. Always use contrasting colors, don't use colors that look painful.
        Include sources from the analysis only if possible. 
        Don't make up stuff (mainly links and facts) or hallucinate anything that's not there in the analysis given to you.

        Don't put too much content on one slide, create an additional slide for the same topic if required.

        Analysis Data:
        {markdown_prompt}

        Return only the HTML code as a string, with no additional explanation or text.
        """
        reveal_js_code = presentation_code_agent(presentation_prompt)

        print("-------PRESENTATION DONE---------")
        
        return {
            "status": "success",
            "markdown": markdown_output,
            "reveal_js": reveal_js_code
        }
    
    except Exception as e:
        # Capture full traceback and print it
        error_trace = traceback.format_exc()
        print("Error occurred:\n", error_trace)  # Logs the full stack trace
        
        raise HTTPException(status_code=500, detail=f"Research failed: {str(e)}")

@app.post("/edit")
async def edit_revealjs_html(request: EditRequest):
    edit_prompt = f"""
    You are a coding assistant specialized in Reveal.js presentations.
    Given the Reveal.js HTML code below, modify it according to the user's prompt.
    Only make changes that maintain valid Reveal.js structure and functionality.
    Return a response in the following format:
    - First, provide an explanation of what changes were made
    - Then, include the complete modified HTML code within triple backticks (```)
    Ensure the code remains a valid Reveal.js presentation using the CDN (https://cdn.jsdelivr.net/npm/reveal.js@4.6.0/dist/).
    Do not redact any part of the code - include all existing content plus the requested changes.

    Original Reveal.js HTML:
    {request.html_input}

    User Prompt:
    {request.prompt}

    Do not mention Reveal.js or any technical details of how you changed.
    Return only the explanation followed by the modified Reveal.js HTML code within ``` marks, with no additional text outside this format. 
    """
    
    result = presentation_code_agent(edit_prompt)
    
    # Split the result into explanation and code
    explanation = result.split("```")[0].strip()
    modified_html = result.split("```")[1].strip()
    
    return {
        "status": "success",
        "result": {
            "explanation": explanation,
            "html": modified_html
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}

def start_ngrok():
    # Set your ngrok auth token (get it from ngrok dashboard)
    ngrok.set_auth_token(os.getenv("NGROK_AUTH_TOKEN"))
    
    # Start ngrok tunnel
    public_url = ngrok.connect(8000, bind_tls=True).public_url
    print(f"ngrok tunnel started at: {public_url}")
    return public_url

def run_server():
    uvicorn.run(app, port=8000)

if __name__ == "__main__":
    # Add NGROK_AUTH_TOKEN to your .env file
    if not os.getenv("NGROK_AUTH_TOKEN"):
        print("Please add NGROK_AUTH_TOKEN to your .env file")
        exit(1)
    
    # Start ngrok in a separate thread
    ngrok_thread = threading.Thread(target=start_ngrok)
    ngrok_thread.start()
    
    # Run the FastAPI server
    run_server()