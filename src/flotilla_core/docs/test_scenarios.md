## Flotilla Test Scenarios (v 0.1)
The goal of the these test scenarios is to identify increasingly complex but realistic scenarios to use in stress testing the Flotilla architecture.  Some scenarios will be intentionally less complex overall but will be designed to stress a particular feature.  These scenarios will be loaded into a LLM session and then run against a current design within the LLM.  They will also be used an inspiration in the creation of example apps to include with the project.


### Simple single user, single agent
A simple single user that submits a text query to a single agent runtime that calls the agent.  The agent is designed to return a punny forecast for a city in the USA.  The agent uses its 3 attached tools to find the correct city and then return its current forecast data.  The agent generates a punny response to the user from this data.  The call to the tools is synchronous and the agent just returns text