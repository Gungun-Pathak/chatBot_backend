from langchain_core.messages import AIMessage, HumanMessage


def serialize_messages(messages):
    """Serialize messages to store in MongoDB"""
    serialized = []
    for msg in messages:
        serialized.append({
            "type": msg.type,
            "content": msg.content
        })
    return serialized


def deserialize_messages(messages):
    """Deserialize messages from MongoDB format to LangChain format"""
    deserialized = []
    for msg in messages:
        if msg['type'] == 'human':
            deserialized.append(HumanMessage(content=msg['content']))
        elif msg['type'] == 'ai':
            deserialized.append(AIMessage(content=msg['content']))
    return deserialized
