import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { useParams } from 'react-router-dom';
import './App.css';

const App = () => {
    const { userId } = useParams(); // Get the unique user ID from the URL
    const [chatHistory, setChatHistory] = useState([]);
    const [jsonData, setJsonData] = useState({});
    const [userInput, setUserInput] = useState('');
    const [options, setOptions] = useState([]);
    const [loading, setLoading] = useState(false); // Loader state
    const [typingMessage, setTypingMessage] = useState('');
    const [isBotTyping, setIsBotTyping] = useState(false);
    const [dataComplete, setDataComplete] = useState(false);

    useEffect(() => {
        // Load initial data when the component mounts
        const loadInitialData = async () => {
            try {
                const response = await axios.post(`http://127.0.0.1:5000/api/initialize`, { userId });
                setJsonData(response.data.current_json);
                setChatHistory(response.data.chat_history || []);
                setOptions(response.data.options || []);
                checkDataCompleteness(response.data.current_json); // Check completeness
            } catch (error) {
                console.error("Error loading initial data:", error);
            }
        };

        loadInitialData();
    }, [userId]);

    useEffect(() => {
        scrollToBottom();
    }, [chatHistory]);

    const scrollToBottom = () => {
        const chatContainer = document.getElementById('chat-container');
        if (chatContainer) {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
    };

    const handleUserInput = async (e) => {
        e.preventDefault();
        if (userInput.trim() === "") return;

        const newChatHistory = [...chatHistory, `User: ${userInput}`];
        setChatHistory(newChatHistory);
        setUserInput('');

        setLoading(true); // Start loader
        const response = await callOpenAIApi(userInput);
        setLoading(false); // Stop loader

        // Simulate bot typing effect
        setIsBotTyping(true);
        setTypingMessage(''); // Clear any previous message
        await simulateTyping(response?.next_reply || '');

        setChatHistory([...newChatHistory, `Bot: ${response?.next_reply}`]);
        setJsonData(response?.current_json);
        setOptions(response?.options);
        checkDataCompleteness(response?.current_json); // Check completeness
    };

    const simulateTyping = async (message) => {
        for (let i = 0; i <= message.length; i++) {
            setTypingMessage(message.slice(0, i));
            await new Promise(resolve => setTimeout(resolve, 50)); // Adjust the delay as needed
        }
        setIsBotTyping(false);
    };

    const handleOptionClick = async (option) => {
        const newChatHistory = [...chatHistory, `User: ${option}`];
        setOptions([]);
        setChatHistory(newChatHistory);

        setLoading(true); // Start loader
        const response = await callOpenAIApi(newChatHistory);
        setLoading(false); // Stop loader

        // Simulate bot typing effect
        setIsBotTyping(true);
        setTypingMessage(''); // Clear any previous message
        await simulateTyping(response?.next_reply || '');

        setChatHistory([...newChatHistory, `Bot: ${response?.next_reply}`]);
        setJsonData(response?.current_json);
        setOptions(response?.options);
        checkDataCompleteness(response?.current_json); // Check completeness
    };

    const callOpenAIApi = async (userInput) => {
        try {
            const response = await axios.post(`http://127.0.0.1:5000/api/chat`, {
                userInput,
                userId
            });

            return {
                current_json: response.data.current_json,
                next_reply: response.data.next_reply,
                options: response.data.options
            };
        } catch (error) {
            console.error("Error calling OpenAI API:", error);
            return {
                current_json: jsonData,
                next_reply: "I'm sorry, I couldn't process your request. Please try again.",
                options: []
            };
        }
    };

    const checkDataCompleteness = (data) => {
        const requiredFields = [
            'Origin_city',
            'budget',
            'destination',
            'firstDestination',
            'food',
            'optimizeType',
            'time_schedule',
            'traveller_type',
            'trip_direction',
            'trip_theme'
        ];

        const isComplete = requiredFields.every(field => {
            if (field === 'destination' && Array.isArray(data[field])) {
                return data[field].length > 0;
            }
            if (field === 'time_schedule') {
                return data[field] &&
                    data[field].duration &&
                    data[field].onward_trip &&
                    data[field].return_trip;
            }
            return data[field] && Object.keys(data[field]).length > 0;
        });

        setDataComplete(isComplete);
    };

    return (
        <div className="min-h-screen bg-gray-100 p-8">
            <h1 className="text-3xl font-bold mb-6">Travel Planner Chatbot</h1>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                    <h2 className="text-2xl font-semibold mb-4">Chatbot</h2>
                    <div id="chat-container" className="bg-white p-4 rounded shadow-md h-96 overflow-y-auto">
                        {chatHistory.map((chat, index) => (
                            <p key={index} className={chat.startsWith('Bot:') ? "text-blue-600" : "text-green-600"}>
                                {chat}
                            </p>
                        ))}
                        {isBotTyping && (
                            <p className="text-blue-600">Bot: {typingMessage}</p>
                        )}
                        {loading && (
                            <div className="typing-indicator mt-2">
                                <div className="dot"></div>
                                <div className="dot"></div>
                                <div className="dot"></div>
                            </div>
                        )}
                        {options?.length > 0 && (
                            <div className="flex flex-wrap mt-2">
                                {options.map((option, index) => (
                                    <button
                                        key={index}
                                        className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold py-2 px-4 m-1 rounded cursor-pointer"
                                        onClick={() => handleOptionClick(option)}
                                    >
                                        {option}
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                    <form onSubmit={handleUserInput} className="mt-4">
                        <input
                            type="text"
                            value={userInput}
                            onChange={(e) => setUserInput(e.target.value)}
                            className="border border-gray-300 p-2 rounded w-full"
                            placeholder="Type your message..."
                        />
                        <button type="submit" className="mt-2 bg-blue-500 text-white px-4 py-2 rounded">
                            Send
                        </button>
                    </form>
                </div>
                <div>
                    <h2 className="text-2xl font-semibold mb-4">Current JSON Data</h2>
                    <pre className="bg-white p-4 rounded shadow-md h-96 overflow-y-auto">{JSON.stringify(jsonData, null, 2)}</pre>
                </div>
            </div>
            <div className="mt-8 p-4 bg-white rounded shadow-md">
                {dataComplete ? (
                    <p className="text-green-600 font-semibold">I have enough data to work with!</p>
                ) : (
                    <p className="text-red-600 font-semibold">Please fill in all the required fields.</p>
                )}
            </div>
        </div>
    );
};

export default App;
