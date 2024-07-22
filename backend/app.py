from flask import Flask, request, jsonify
from flask_cors import CORS
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from typing import List, Dict, Optional
import json
from dotenv import load_dotenv
import os
from langchain.memory import ConversationBufferMemory
import os
from flask_caching import Cache
from langchain_community.tools import DuckDuckGoSearchRun

load_dotenv()

openai_api_key = os.getenv("OPEN_API_KEY")


search = DuckDuckGoSearchRun()


class FieldUpdate(BaseModel):
    field_name: str
    answer: str

class ResponseStructure(BaseModel):
    inferences: Optional[List[FieldUpdate]] = None
    next_reply: str
    metadata:str
    reason:str
    internet_search_required: bool = Field(default=False, description="Flag indicating if internet search is required")
    online_search_query: Optional[str] = Field(default=None, description="Query to search online for better GPT-4 responses")

app = Flask(__name__)
CORS(app)


app.secret_key = 'your_secret_key'  # Replace with a secure key
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})  # Use SimpleCache for in-memory


initialJson = {
    "Origin_city": {},
    "budget": {},
    "destination": [],
    "firstDestination": {},
    "food": {},
    "optimizeType": {},
    "time_schedule": {
      "duration": {
        "unit": {},
        "value": {}
      },
      "onward_trip": {
        "date": {
          "day_of_month": {},
          "month": {},
          "year": {}
        },
        "time": {
          "hour": {},
          "minute": {}
        }
      },
      "return_trip": {
        "date": {
          "day_of_month": {},
          "month": {},
          "year": {}
        },
        "time": {
          "hour": {},
          "minute": {}
        }
      }
    },
    "traveller_type": {},
    "trip_direction": {},
    "trip_theme": {},
    "user_interests": {
      "adult": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "any": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "beach": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "city-sightseeing": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "culture and traditions": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "dark tourism": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "food and wine": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "historical": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "kids entertainment": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "nature": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "nightlife": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "outdoors and sports": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "religion": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "science and technology": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "shopping": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      },
      "theatre and concert": {
        "places": [],
        "user_keywords": [],
        "user_selected": False,
        "weight": 0
      }
    }
  }

initial_message = ["Bot: Hello! I am here to help you plan your vacation. Let's get started! Where are you planning to visit this time for vacation?"]


@app.route('/api/initialize', methods=['POST'])
def initialize():
    data = request.json
    user_id = data.get('userId', '')

    print("++++++++++++++",user_id,"++++++++++++++")


    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    if not cache.get(user_id):
        cache.set(user_id, {
            'chat_history': initial_message,
            'current_json': initialJson,
            "options": []
        })

    user_data = cache.get(user_id)
    return jsonify({
        'chat_history': user_data['chat_history'],
        'current_json': user_data['current_json'],
        "options": user_data['options']
    })



@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_input = data.get('userInput', '')
    user_id = data.get('userId', '')

    print("++++++++++++++",user_id,"++++++++++++++",user_input,"++++++++++++++")



    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400
    
    # Retrieve the current chat history and json data for the user
    user_data = cache.get(user_id)
    chat_history = user_data['chat_history']
    current_json = user_data['current_json']

    chat_history.append(f"User: {user_input}")

    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    for chat in chat_history:
        if chat.lower().startswith('user:'):
            role = "user"
            content = chat.split(': ', 1)[1]  # Remove "User:" from the content
        elif chat.lower().startswith('bot:'):
            role = "assistant"
            content = chat.split(': ', 1)[1]  # Remove "Bot:" from the content
        else:
            # Default role or handle cases where prefix is not recognized
            role = "user"
            content = chat
        
        messages.append({"role": role, "content": content})
    
    try:
        current_json, next_reply, options = call_openai_api(messages, flatten_json(current_json))

        # Append the response to chat history
        chat_history.append(f"Bot: {next_reply}")

        cache.set(user_id, {
            'chat_history': chat_history,
            'current_json': current_json,
            "options": options
        })

        # # Update the session data
        # session[user_id] = {
        #     'chat_history': chat_history,
        #     'current_json': current_json
        # }

        return jsonify({
            "current_json": current_json,
            "next_reply": next_reply,
            "options": options
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



def call_openai_api(chat_history, current_json):

    model = ChatOpenAI(api_key=openai_api_key, temperature=0.5, model="gpt-4")
    # model = ChatOpenAI(api_key=openai_api_key, temperature=0)

    # Define the parser
    parser = JsonOutputParser(pydantic_object=ResponseStructure)

    details = {
        "fields": [
            {
                "field_name": "optimizeType",
                "question": "Would you prefer to sequence the list of cities manually, or should we auto-sequence them for you?",
                "options": ["manual", "auto"]
            },
            {
                "field_name": "firstDestination",
                "question": "Where would you like to go first?"
            },
            {
                "field_name": "trip_theme",
                "question": "What is the theme of your trip (e.g., adventure, beach, cultural)?",
                "options": [
                    "romantic",
                    "family-vacation",
                    "eco-tourism",
                    "party",
                    "roadtrip",
                    "remote-work",
                    "business-work",
                    "health and wellness",
                    "spiritual",
                    "lbgtq+",
                    "adventure",
                    "general-tourism-no-theme"
                ]
            },
            {
                "field_name": "destination",
                "question": "Could you provide the list of destinations you plan to visit?",
                "instruction": "this will be a list so even in inference give back a list. if the user updates this then also give the final list in inference as whatever you give will be replaced with previous value"
            },
            {
                "field_name": "traveller_type",
                "question": "What type of traveler are you (e.g., solo, family, friends)?",
                "options": [
                    "solo",
                    "couple",
                    "family-no kids",
                    "family-with kids",
                    "friends"
                ]
            },
            {
                "field_name": "Origin_city",
                "question": "What is your city of origin?"
            },
            {
                "field_name": "budget",
                "question": "How would you describe your budget for this trip?",
                "options": [
                    "on a tight budget",
                    "comfortable spending",
                    "happy to spend for a luxurious vacation"
                ]
            },
            {
                "field_name": "food",
                "question": "Do you have any dietary preferences?",
                "options": [
                    "any",
                    "Middle-eastern",
                    "indian",
                    "asian",
                    "european",
                    "mexican",
                    "vegetarian",
                    "south american",
                    "vegan",
                    "seafood",
                    "fast food",
                    "cafe",
                    "dessert",
                    "healthy",
                    "bar/pub",
                    "barbeque",
                    "pizza"
                ]
            },
            {
                "field_name": "trip_direction",
                "question": "Is your trip one-way or round-trip?",
                "options": ["return", "oneway"]
            },
            {
                "field_name": "time_schedule_onward_trip_time_hour",
                "question": "At what time would you like to depart?",
                "value_option":  ["AM/PM" , "24Hour"],
                "instructions": "user needs to specify if the time is in am or pm or in 24 hour format if you cannot infer this then ask user for clarification"
            },
            {
                "field_name": "time_schedule_onward_trip_time_minute",
                "question": "Minute:"
            },
            {
                "field_name": "time_schedule_onward_trip_date_day_of_month",
                "question": "Day of the month:",
                "options": [1, 31]
            },
            {
                "field_name": "time_schedule_onward_trip_date_month",
                "question": "Month:",
                "options": [1, 12]
            },
            {
                "field_name": "time_schedule_onward_trip_date_year",
                "question": "Year:",
                "options": ["current_year", "next_year"]
            },
            {
                "field_name": "time_schedule_return_trip_time_hour",
                "question": "At what time would you like to depart?",
                "value_option":  ["AM/PM" , "24Hour"],
                "instructions": "user needs to specify if the time is in am or pm or in 24 hour format if you cannot infer this then ask user for clarification"
            },
            {
                "field_name": "time_schedule_return_trip_time_minute",
                "question": "Minute:"
            },
            {
                "field_name": "time_schedule_return_trip_date_day_of_month",
                "question": "Day of the month:",
                "options": [1, 31]
            },
            {
                "field_name": "time_schedule_return_trip_date_month",
                "question": "Month:",
                "options": [1, 12]
            },
            {
                "field_name": "time_schedule_return_trip_date_year",
                "question": "Year:",
                "options": ["current_year", "next_year"]
            },
            {
                "field_name": "time_schedule_duration_value",
                "question": "Duration value:"
            },
            {
                "field_name": "time_schedule_duration_unit",
                "question": "Duration unit:",
                "options": ["week", "month", "days"]
            },
            {
                "field_name": "user_interest_interest-name",
                "instructions": "Observe the conversation context and user input to infer the user's general interests for the trip. Set appropriate values for weight, user_selected, places, and user_keywords based on the discussion. Remember each field which you set true will start with an innitial weight of 0.5 and wiill increase by 0.1 every if user shows more interest in it (if he metions it again or says something to  indicates that he is more interested in that field. also allow the user to update the it anything they like. also in th ekeywords you have to records that user said that shows his interest in that) also if the user mentions any specific places regarding that then they should be in the respective places list field"
            }
        ]
    }


    query = f"""

            You are a travel assistant chatbot. Your name is Travel.AI, and you are designed to help users plan their trips and provide travel-related information. First, you need to get some information from the user. You will receive the current conversation history and a JSON template with the questions that need to be filled based on user inputs.

            You have to interact with the user as a customer service agent and get them to answer questions in order to fill the question JSON template. Ensure your responses are polite, engaging, and context-aware, using natural language to guide the user through the necessary details. Here are some key points to remember:

         
            1. Engage politely, analyze chat history, and provide informative responses.
            2. Analyze chat history carefully before responding, providing inferences only when appropriate.
            3. Each response should be informative and contain at least 20 words.
            4. If the user seems confused or requests suggestions then respond accordingly and guide them. base your suggestion on the questions already answered.
            5. If the user refuses to answer, skip the question and try again later in a different way. if user skips again then mention how important it is to get that data for you and try to convince user.
            6. Allow for updates and deletions of answers.
            7. Only give inferences when you have the answer; do not guess. If needed ask user for clarification in your next reply. also if you cannot match the answer to the value options then ask the user to clarify
            8. Clearly state reasons for inferences or why you're not providing one.
            9. For questions with options, specify the field name accurately in metadata; avoid providing options in next_reply.
            10. if the user provided the start and end date and time of the trip then be smart enought to calculate the duration. and if you need clarification then ask for it in next reply.
            11. keep an eye on the user latest input to fill user interest fields( that start with user_interest as the prefix) accordingly as explained in the details.
            12. never ask the questions for which a clear answer is already present. only if you wish to clarify it then you can ask
            13. be extra careful when asking for date and time. you can club those questions together.
            14. Update user interest fields based on user inputs and instructions mentioned in details json below.
            15. also if user selects manual sequencing then ask him to write the cities name in order and in the inferences give the answer in the same order 
            16. At the end of the chat confirm and clarify with the user the interested you have collected so far. and if the interests are not collected then ask user his interests.
            17. if the user is normally greeting like saying hi hello then greet them normally and introduce yourself (intro is important) say You are a travel assistant chatbot named Travel.AI, designed to help users plan their trips and provide travel-related information and how you need some info to do that.
            18. Ensure all fields are answered before saying "Thank you, I have all I need for now."
            19. if the user asks something that you dont have enough information to answer or you thing you can answer better if you have internet search results then in your response give "internet_search_required": true else set it to false always. Additionally, if you decide to perform an internet search, provide a meaningful value for "online_search_query" that reflects the specific information you intend to search for As i will search this query "online_search_query" online and call make this gpt call again with the search results.
            20. finally the most important thing is that your order and time of asking each question should not be ambigious. it should make sense, if the user is asking about a place or any other thing then resolve that first and ask the user if he have any more query. and only after the user's query has been answered then from there keeping the context in mind ask the next question in a relevant wany. dont just answer and ask the next question that is irrelevant. interact just like an professional customer support helping and guiding the user along

            always ask the questions in a logically sensible way


            Details on each field and how to ask questions: {json.dumps(details, indent=4)}

            Please ensure responses are informative, accurate, and tailored to the user's queries and preferences. Use natural language to engage users and provide a seamless experience throughout their travel planning journey.

            Below are a few examples for you to learn how to do it:

            
            Examples:
                Bot: Hello! I am here to help you plan your vacation. Let's get started! Where are you planning to go for vacation this time?
                User: hello.

                {{
                    "inferences": [],
                    "next_reply": "Hi there! It's nice to meet you. I'm Travel.AI, your travel assistant. I'm here to help you plan your trip. Could you please tell me where you would like to go first?",
                    "metadata": "firstDestination",
                    "reason": "The user greeted the assistant. The assistant introduced itself and asked the first question to start the travel planning process.",
                    "internet_search_required": false
                }}

                User: I want to visit several cities in Europe.
                {{
                    "inferences": [],
                    "next_reply": "Great! Can you list the cities you plan to visit?",
                    "metadata": "none",
                    "reason": "User mentioned visiting several cities, asking for a list.",
                    "internet_search_required": false
                }}

                User: Paris, Rome, and Barcelona.
                {{
                    "inferences": [
                        {{"field_name": "destination", "answer": ["Paris", "Rome", "Barcelona"]}}
                    ],
                    "next_reply": "Do you want to manually sequence the cities you will visit, or should we auto-sequence it?",
                    "metadata": "none",
                    "reason": "User provided list of cities: Paris, Rome, Barcelona.",
                    "internet_search_required": false
                }}

                User: Let's auto-sequence it.
                {{
                    "inferences": [
                        {{"field_name": "optimizeType", "answer": "auto"}}
                    ],
                    "next_reply": "What is your origin city for this trip?",
                    "metadata": "none",
                    "reason": "User chose auto-sequencing.",
                    "internet_search_required": false
                }}

                User: I will start from New York.
                {{
                    "inferences": [
                        {{"field_name": "Origin_city", "answer": "New York"}}
                    ],
                    "next_reply": "How would you describe your budget for this trip? Please choose from: 'on a tight budget', 'comfortable spending', 'happy to spend for a luxurious vacation'.",
                    "metadata": "budget",
                    "reason": "User mentioned New York as the origin city.",
                    "internet_search_required": false
                }}

                User: Comfortable spending.
                {{
                    "inferences": [
                        {{"field_name": "budget", "answer": "comfortable spending"}}
                    ],
                    "next_reply": "Do you have any dietary preferences or restrictions? Please choose from: 'any', 'Middle-eastern', 'indian', 'asian', 'european', 'mexican', 'vegetarian', 'south american', 'vegan', 'seafood', 'fast food', 'cafe', 'dessert', 'healthy', 'bar/pub', 'barbeque', 'pizza'.",
                    "metadata": "food",
                    "reason": "User chose 'comfortable spending' as budget.",
                    "internet_search_required": false
                }}

                User: I prefer European cuisine.
                {{
                    "inferences": [
                        {{"field_name": "food", "answer": "european"}}
                    ],
                    "next_reply": "What is your preferred start date and time of your trip?",
                    "metadata": "none",
                    "reason": "User prefers European cuisine.",
                    "internet_search_required": false
                }}


            Remember these are just examples for you to learn. do not use this example data in real inferences
            and also remember that if user selects manula sequencing then ask him the order of his visit and arrange them in the same order in your response inferences. 
            if only one city is given ask the user to clarify if he is visiting only one city. if yes then also set sequencing to manual and no need to prompt the user for that.
            Also the first destination is also a destination so it should be added to destination list also
            also the sequencing related questions should be asked only after the user has given the cities. and is visiting multiple cities
           
            Chat history:
            {chat_history}

            Questions that need to be answered (some of them have been answered; focus on those that are still not answered):
            {json.dumps(current_json, indent=4)}

            your output json should have this structure :

            {{
                "inferences": [ your inferences based on th euser input],
                "next_reply": "next reply to give to the user",
                "metadata": "this will contain the field name of the question you are asking in the next_reply if that field has value options to choose from. if you are suggestion and not asking any question from the current json then just state 'none' here", also this value should be none for user interest fields,
                "reason": "here you have to give your reasons for whatever inference you gave along with latest user input. example - i am giving inference for destination to be tokyo as the user mentioned tokyo in this latest input ie. 'i wish to to to tokyo' and if you are leaving the inference empty then state why so",
                "internet_search_required": "if the user's laset input is asking something that you think you will be able to answer better if you have the internet search results, otherwise if user is conversing normally and you dont need the the internet search result then set to its default value which is false",
                "online_search_query": "if you decide to 'internet_search_required': true , ie if you decide that you want internet search result then here kive the specific query you need me to search online and give you the result when making this gpt call again for better response"

            }}

            also you can give inferences even for a one word answer based on the context from the chat_hist0ry

            just be extra careful when filling time no matter in what format the user enters time you have to always convert it to 24 hour format. and be smart enough to infer minutes as 00 when the user just only provides the hours


            And finally the most important thing is you have the value options provided in the details json so make sure for the questions with value options you only infer the answer from among those options. if you cannot do that then ask user for clarification or you can also ask him to select themselves

            just give me the json structured output nothing else


            also if the user is not asking something that is not relevant to our travel planning they dont give answer to that query (important) just say that 'please stick to travel related query only' to the user
            """


    # Define the prompt template
    prompt = PromptTemplate(
        template="""Answer the user query.\n{query}\n""",
        input_variables=["query"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )

    # Create the LLMChain
    chain = prompt | model | parser

    # Prepare the input for the chain
    input_data = {
        "query":query
    }

    # Invoke the chain
    response = chain.invoke({"query":query})
    
    
    # Convert response to dictionary
    print(chat_history[-1],"     response:", json.dumps(response, indent=4))
    updated_json = response

        # Update the current JSON with the new answers
    if "inferences" in updated_json and updated_json["inferences"]:
        for update in updated_json["inferences"]:
            if current_json[update["field_name"]] == "destination":
                current_json[update["field_name"]] = list(set(current_json["destination"].append(update["answer"])  ))
            else:
                current_json[update["field_name"]] = update["answer"]



    if response['internet_search_required']:
        online_search_query = response['online_search_query']
        if online_search_query:
            print("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
            search_results = search.run(online_search_query)
            # Define the prompt template
            prompt = PromptTemplate(
                template="""Answer the user query, also use the context info (ie the internet search results that i am providing you already so dont ask for it again) if required and give a very detailed length answer to the user.\n contest info :{search_results}\n\n{query}\n""",
                input_variables=["query"],
                partial_variables={"format_instructions": parser.get_format_instructions()},
            )

            # Create the LLMChain
            chain = prompt | model | parser

            # Prepare the input for the chain
            input_data = {
                "query":query,
                "search_results":search_results
            }

            # Invoke the chain
            response = chain.invoke({"query":query, "search_results":search_results})
            print(chat_history[-1],"     response:", json.dumps(response, indent=4))
            updated_json = response
            # print(search_results)
            print("|||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
            # Perform online search using DuckDuckGoSearchRun
            # search_results = search.run(online_search_query)



    return unflatten_json(current_json), updated_json.get("next_reply", ""), get_options(updated_json.get("metadata", ""))





def flatten_json(nested_json):
    flat_json = {}

    flat_json["optimizeType"] = nested_json.get("optimizeType", {})
    flat_json["firstDestination"] = nested_json.get("firstDestination", {})
    flat_json["trip_theme"] = nested_json.get("trip_theme", {})
    flat_json["destination"] = nested_json.get("destination", [])
    flat_json["traveller_type"] = nested_json.get("traveller_type", {})
    flat_json["Origin_city"] = nested_json.get("Origin_city", {})
    flat_json["budget"] = nested_json.get("budget", {})
    flat_json["food"] = nested_json.get("food", {})
    flat_json["trip_direction"] = nested_json.get("trip_direction", {})

    time_schedule = nested_json.get("time_schedule", {})
    onward_trip = time_schedule.get("onward_trip", {})
    return_trip = time_schedule.get("return_trip", {})
    duration = time_schedule.get("duration", {})

    flat_json["time_schedule_onward_trip_time_hour"] = onward_trip.get("time", {}).get("hour", {})
    flat_json["time_schedule_onward_trip_time_minute"] = onward_trip.get("time", {}).get("minute", {})
    flat_json["time_schedule_onward_trip_date_day_of_month"] = onward_trip.get("date", {}).get("day_of_month", {})
    flat_json["time_schedule_onward_trip_date_month"] = onward_trip.get("date", {}).get("month", {})
    flat_json["time_schedule_onward_trip_date_year"] = onward_trip.get("date", {}).get("year", {})

    flat_json["time_schedule_return_trip_time_hour"] = return_trip.get("time", {}).get("hour", {})
    flat_json["time_schedule_return_trip_time_minute"] = return_trip.get("time", {}).get("minute", {})
    flat_json["time_schedule_return_trip_date_day_of_month"] = return_trip.get("date", {}).get("day_of_month", {})
    flat_json["time_schedule_return_trip_date_month"] = return_trip.get("date", {}).get("month", {})
    flat_json["time_schedule_return_trip_date_year"] = return_trip.get("date", {}).get("year", {})

    flat_json["time_schedule_duration_value"] = duration.get("value", {})
    flat_json["time_schedule_duration_unit"] = duration.get("unit", {})

    user_interests = nested_json.get("user_interests", {})
    for key, value in user_interests.items():
        flat_json[f"user_interest_{key}_weight"] = value.get("weight", 0)
        flat_json[f"user_interest_{key}_user_selected"] = value.get("user_selected", False)
        flat_json[f"user_interest_{key}_places"] = value.get("places", [])
        flat_json[f"user_interest_{key}_user_keywords"] = value.get("user_keywords", [])

    return flat_json

def unflatten_json(flat_json):
    nested_json = {}

    nested_json["optimizeType"] = flat_json.get("optimizeType", {})
    nested_json["firstDestination"] = flat_json.get("firstDestination", {})
    nested_json["trip_theme"] = flat_json.get("trip_theme", {})
    nested_json["destination"] = flat_json.get("destination", [])
    nested_json["traveller_type"] = flat_json.get("traveller_type", {})
    nested_json["Origin_city"] = flat_json.get("Origin_city", {})
    nested_json["budget"] = flat_json.get("budget", {})
    nested_json["food"] = flat_json.get("food", {})
    nested_json["trip_direction"] = flat_json.get("trip_direction", {})

    time_schedule = {}
    onward_trip = {}
    return_trip = {}
    duration = {}

    onward_trip["time"] = {
        "hour": flat_json.get("time_schedule_onward_trip_time_hour", {}),
        "minute": flat_json.get("time_schedule_onward_trip_time_minute", {})
    }
    onward_trip["date"] = {
        "day_of_month": flat_json.get("time_schedule_onward_trip_date_day_of_month", {}),
        "month": flat_json.get("time_schedule_onward_trip_date_month", {}),
        "year": flat_json.get("time_schedule_onward_trip_date_year", {})
    }

    return_trip["time"] = {
        "hour": flat_json.get("time_schedule_return_trip_time_hour", {}),
        "minute": flat_json.get("time_schedule_return_trip_time_minute", {})
    }
    return_trip["date"] = {
        "day_of_month": flat_json.get("time_schedule_return_trip_date_day_of_month", {}),
        "month": flat_json.get("time_schedule_return_trip_date_month", {}),
        "year": flat_json.get("time_schedule_return_trip_date_year", {})
    }

    duration = {
        "value": flat_json.get("time_schedule_duration_value", {}),
        "unit": flat_json.get("time_schedule_duration_unit", {})
    }

    time_schedule["onward_trip"] = onward_trip
    time_schedule["return_trip"] = return_trip
    time_schedule["duration"] = duration

    nested_json["time_schedule"] = time_schedule

    user_interests = {}
    for key in flat_json:
        if key.startswith("user_interest_"):
            interest_key = key.split("_")[2]  # Extracting the interest key from the flattened key
            user_interests[interest_key] = {
                "weight": flat_json.get(f"user_interest_{interest_key}_weight", 0),
                "user_selected": flat_json.get(f"user_interest_{interest_key}_user_selected", False),
                "places": flat_json.get(f"user_interest_{interest_key}_places", []),
                "user_keywords": flat_json.get(f"user_interest_{interest_key}_user_keywords", [])
            }
    
    nested_json["user_interests"] = user_interests

    return nested_json



def get_options(field_name):
    options_list = {
        "trip_theme": [
            "romantic", "family-vacation", "eco-tourism", "party", 
            "roadtrip", "remote-work", "business-work", "health and wellness", 
            "spiritual", "lbgtq+", "adventure", "general-tourism-no-theme"
        ],
        "traveller_type": [
            "solo", "couple", "family-no kids", "family-with kids", "friends"
        ],
        "budget": [
            "on a tight budget", "comfortable spending", 
            "happy to spend for a luxurious vacation"
        ],
        "food": [
            "any", "Middle-eastern", "indian", "asian", "european", 
            "mexican", "vegetarian", "south american", "vegan", 
            "seafood", "fast food", "cafe", "dessert", "healthy", 
            "bar/pub", "barbeque", "pizza"
        ],
        "trip_direction": [
            "return", "oneway"
        ],
        "optimizeType": [
            "manual", "auto"
        ],
        "time_schedule_duration_unit": [
            "week", "month", "days"
        ],
        "time_schedule_onward_trip_date_year": [
            "current_year", "next_year"
        ],
        "time_schedule_return_trip_date_year": [
            "current_year", "next_year"
        ]
    }
    if field_name in options_list:
        return options_list[field_name]
    else:
        return []


if __name__ == '__main__':
    app.run(debug=True)
