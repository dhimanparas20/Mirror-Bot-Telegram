# Run this script to extract client_email from accounts folder into a comma seperated text file .
import os
import json

# Path to the directory containing JSON files
directory = 'accounts'

# Initialize a list to store client emails
client_emails = []

# Loop through each JSON file in the directory
for filename in os.listdir(directory):
    if filename.endswith('.json'):
        file_path = os.path.join(directory, filename)
        
        # Open and read the JSON file
        with open(file_path, 'r') as file:
            data = json.load(file)
            client_email = data.get('client_email')
            
            # Append the client email to the list
            if client_email:
                client_emails.append(client_email)

# Join all emails with a comma and write to a text file
with open('client_emails.txt', 'w') as output_file:
    output_file.write(','.join(client_emails))

print("Client emails have been written to client_emails.txt")
