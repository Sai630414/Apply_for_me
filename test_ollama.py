import asyncio
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

async def main():

    llm = ChatOllama(
        model="qwen2.5:3b",
        base_url="http://localhost:11434",
        temperature=0.3,
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
            You are an expert job application writing assistant.

            Write answers on behalf of the applicant,
            in the first person.

            Never describe yourself as an AI.
            Never say you cannot apply for jobs.
            Never mention Alibaba Cloud.

            Use only the applicant information provided.
            Never invent qualifications or experience.

            Return only the answer.
            """
        ),
        (
            "human",
            """
            Applicant profile:
            Third-year Computer Science student.
            Skills: Python, React, JavaScript, Docker and AWS.
            Projects: Full-stack applications and cloud deployments.

            Company: Paytm
            Role: Software Engineering Intern

            Question:
            Why are you interested in joining Paytm?

            Write a natural answer in 80 words.
            """
        )
    ])

    chain = prompt | llm

    response = await chain.ainvoke({})

    print("\nGenerated answer:\n")
    print(response.content)


if __name__ == "__main__":
    asyncio.run(main())