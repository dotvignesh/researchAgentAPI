from fastapi import FastAPI, HTTPException
from smolagents import CodeAgent, DuckDuckGoSearchTool, VisitWebpageTool
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

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_market_research_agent():
    model = OpenAIServerModel(
        model_id="gpt-4o-mini",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    web_tools = [DuckDuckGoSearchTool()]
    
    web_search_agent = CodeAgent(
        model=model,
        tools=web_tools,
        verbosity_level=2,
        name="web_search_agent",
        description="A sub-agent that searches the internet to gather data."
    )
    
    manager_agent = CodeAgent(
        model=model,
        tools=web_tools,
        verbosity_level=2,
        managed_agents=[web_search_agent],
        additional_authorized_imports=["requests", "os", "json"]
    )
    return manager_agent

def create_presentation_agent():
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
presentation_agent = create_presentation_agent()

# [Your existing generate_reveal_js_code function remains the same]
def generate_reveal_js_code(analysis_json: str) -> str:
    prompt = f"""
    You are a coding assistant tasked with generating a Reveal.js presentation based on a market research analysis. Given the JSON analysis below, create a complete HTML file with Reveal.js setup and slides. Include only the necessary content from the analysis, create as many slides as required.

    Use the Reveal.js CDN (https://cdn.jsdelivr.net/npm/reveal.js@4.6.0/dist/). Use clean and minimalistic styling - it should look professional like how Apple's PPTs would look. But don't make it look very boring. Always use contrasting colors, don't use colors that look painful.
    Include sources from the analysis only if possible. 
    Don't make up stuff (mainly links and facts) or hallucinate anything that's not there in the analysis given to you.

    Analysis JSON:
    {json.dumps(analysis_json)}

    Return only the HTML code as a string, with no additional explanation or text.
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000
    )
    return response.choices[0].message.content.strip()

import traceback  # Add this import at the top

import traceback  # For detailed error logging

@app.post("/research/presentation")
async def conduct_research_and_present(request: ResearchRequest):
    try:
        research_prompt = f"""
        You are a world-class market research consultant with credentials from top institutions such as INSEAD and Harvard. Your task is to perform a rigorous, data-driven analysis solely based on real-time research conducted using the available web tool. You must ALWAYS and without exception use the web tool to retrieve *only factual, up-to-date information* from highly credible online sources. Do not rely on any pre-existing internal knowledge or unverified content—every data point in your analysis must be backed by a web-sourced reference (include source URLs).

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

        Return only the structured JSON response, STRICTLY ONLY AFTER YOU HAVE COMPLETED ALL YOUR ANALYSIS, with no additional commentary or explanation.
        """


        
        print("-------STARTING RESEARCH---------")
        
        # Run the research agent
        analysis_json = market_research_agent.run(research_prompt)
        
        print("-------ANALYSIS DONE---------")
        
        if isinstance(analysis_json, str):
            # Remove markdown code fences if present
            cleaned = analysis_json.strip()
            if cleaned.startswith("```"):
                # Remove the first line if it's a code fence
                lines = cleaned.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                # Remove the last line if it's a code fence
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                cleaned = "\n".join(lines).strip()
            try:
                analysis_data = json.loads(cleaned)
            except json.JSONDecodeError:
                print("Error: Research agent returned invalid JSON!")
                print("Response received:", cleaned)
                raise HTTPException(status_code=500, detail="Research agent returned invalid JSON.")
        elif isinstance(analysis_json, dict):
            analysis_data = analysis_json
        else:
            print("Unexpected response type:", type(analysis_json))
            raise HTTPException(status_code=500, detail="Unexpected data format from research agent.")


        # Generate markdown summary
        presentation_prompt = f"""
        You are a presentation generator. Given the market research analysis JSON below, create a clean, concise Markdown summary of the analysis. Focus on clarity and professionalism.

        Analysis JSON:
        {json.dumps(analysis_data)}

        Return only the Markdown string, no additional text.
        """

        print("-------GENERATING MARKDOWN---------")
        
        markdown_output = presentation_agent.run(presentation_prompt)

        print("-------MARKDOWN DONE---------")
        
        # Generate Reveal.js code
        print("-------GENERATING REVEAL.JS PRESENTATION---------")
        reveal_js_code = generate_reveal_js_code(analysis_data)

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