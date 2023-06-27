import openai
import os
import requests
from tenacity import retry,wait_random_exponential,stop_after_attempt
from termcolor import colored
from dotenv import dotenv_values
import streamlit as st
import pandas as pd
import json
from streamlit_modal import Modal

import sqlite3

GPT_MODEL = "gpt-3.5-turbo-0613"
config = dotenv_values(".env")
openai.api_key= config['OPENAI_API_KEY']

input_user = st.text_input("Ask a Question")

class Conversation: 
        def __init__(self) :
            self.conversation_history = []

        def add_message(self,role,content):
            message = {"role":role,"content":content}
            self.conversation_history.append(message)


        def display_conversation(self):

            role_to_color = {
                "system":"red",
                "user":"green",
                "assistant":"blue",
                "function":"magenta"
            }
            for message in self.conversation_history :
                print(
                colored(
                    f"{message['role']}:{message['content']}\n\n",
                    role_to_color[message["role"]],
                )
                )
               




sql_convo=Conversation()

if st.button('Ask Question') :

    conn = sqlite3.connect("data\chinook.db")
    st.write("Database Succesfully Opened")
    print ("Database Sucesfully Opened")
   

    def chat_completion_request(messages:list,functions=None,model = GPT_MODEL):
        if functions is not None:
            try:
                response = openai.ChatCompletion.create(
                    model = model,
                    messages = messages,
                    temperature = 0.1,
                    max_tokens=512,
                    functions=functions,

                )
                print(response)
                return response
            except Exception as e:
                print("Unable to generate ChatCompletion response")
                print(f"Exception: {e}")
                return e



    def get_table_names(conn):
        """Return a list of table names"""
        table_names = []
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type ='table';")
        for table in tables.fetchall():
            table_names.append(table[0])
        return table_names

    def get_column_names(conn,name):
        column_names = []
        columns = conn.execute(f"PRAGMA table_info('{name}');").fetchall()
        for col in columns:
            column_names.append(col[1])
        return column_names

    def get_database_info(conn):
        table_dicts = []

        for table_name in get_table_names(conn):
            column_names = get_column_names(conn,table_name)
            table_dicts.append({"table_name":table_name,"column_names":column_names})
        return table_dicts


    database_schema_dict = get_database_info(conn)

    database_schema_string = "\n".join(
        [
            f"Table: {table['table_name']}\nColumns : {','.join(table['column_names'])}"
            for table in database_schema_dict
        ]
    )

    functionsa = [
        {
            "name":"ask_database",
            "description":"Use this function to answer the user questions about the database . Output should be a fully formed SQL query.",
            "parameters":{
                "type":"object",
                "properties":{
                    "query":{
                        "type":"string",
                        "description":f"""
                                SQL query extracting info to answer the user's question.
                                SQL should be written using this database schema:
                                {database_schema_string}
                                The query should be returned in plain text with space using escape character to differentiate between syntax 
                                for example SELECT *\n FROM table\n WHERE x = 10, not in JSON
                        """
                    }
                }
            },
            "required":["query"],
        }
    ]
    def ask_database(conn,query):
        """
        Function to query SQLite database with provided SQL query.

        Parameters:
        conn(sqlite3.Connection)
        query(str)
        """

        try:
            results = conn.execute(query).fetchall()
            
            return results
            
        except Exception as e:
            raise Exception(f"SQL error : {e}")
        

    def chat_completion_with_function_execution(messages,functions=None):
        try:
            response = chat_completion_request(messages,functions)
            print(response)
            # print(response)
        
            full_message = response["choices"][0]

            if full_message["finish_reason"] == "function_call":
                print(f"function generation requested, calling function")
                return call_function(messages,full_message)
            
            else :
                print(f"Function not required, responding to user")
                return response
        except Exception as e:
            print("Unable to generate ChatCompletion Response")
            print(f"Exception : {e}")

            return response

    def call_function(messages,full_messages):
        if full_messages["message"]["function_call"]["name"] == "ask_database":
            query = eval(full_messages["message"]["function_call"]["arguments"])
            print(f"prepped query is {query}")
            # st.write(query)
            df=pd.read_sql_query(query["query"],conn)
            # st.dataframe(df )
            # st.dataframe(df)
            # st.bar_chart(dataframe)
            try:
                results = ask_database(conn,query["query"])
                # st.write(results)
                
                print(results)
            
            except Exception as e:
                print(e)

                messages.append(
                    {
                        "role":"system",
                        "content":f"""Query: {query['query']}
                        the previous query received the error {e}.
                        Please return a fixed SQL query in plain text.
                        Your response should consist of only the sql query with the separator sql_start at 
                        the beginning and sql_end at the end
                        """,
                    }
                )
                reponse = chat_completion_request(messages, model="gpt-3.5-turbo-0613")
                
                try :
                    cleaned_query =reponse.json()["choices"][0]["message"]["content"].split("sql_start")[1]

                    cleaned_query = cleaned_query.split("sql_end")[0]

                    print(cleaned_query)

                    results = ask_database(conn,cleaned_query)
                    print(results)
                    print("Got on second try")
                except Exception as e:
                    print("Second Failure, exiting")

                    print("Function execution failed")
                    print (f"Error Message: {e}")

            messages.append(
                {"role":"function","name":"ask_database","content":str(results)}
            )

            return query["query"]
            # print(messages)
            # try:
            #     # response = chat_completion_request(messages,functions=functionsa,model="gpt-3.5-turbo-0613")
            #     response = query
            #     # print(response)
            #     return response
            # except Exception as e:
            #     print(type(e))
            #     print(e)
            #     raise Exception("Function chat request failed")
        else:
            raise Exception("Function does not exist and cannot be called") 

    

    
    agent_system_message = """You are AG-BOT, a helpful assitant who gets answers to user questions from the Database Available.
    Provide as many details as prossible to your users
    """



    
    sql_convo.add_message('system',agent_system_message)
    sql_convo.add_message('user',input_user)


    chat_response = chat_completion_with_function_execution(
        sql_convo.conversation_history,functions=functionsa
    )

    try:
        # assistant_message = chat_response["choices"][0]["message"]["content"]
        assistant_message = chat_response
        print(assistant_message)
    except Exception as e:
        print(e)
        print(chat_response)


    sql_convo.add_message("assistant",assistant_message)
    

    st.code(assistant_message,language='sql')



