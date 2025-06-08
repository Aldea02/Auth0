# FastAPI Auth0 Authentication

A FastAPI application with Auth0 authentication that supports Google OAuth, GitHub OAuth, and username/password login.

## Features

- **Health Check Endpoint**: Verify the API is running
- **Auth0 Integration**: 
  - Username and password authentication via Auth0 Universal Login
  - Google OAuth authentication
  - GitHub OAuth authentication
  - Protected routes requiring authentication
- **API Documentation**: Auto-generated with Swagger UI and ReDoc

## Auth0 Setup

Before running the application, you need to set up Auth0:

1. Create an [Auth0 account](https://auth0.com/) if you don't have one
2. Create a new API in Auth0:
   - Name it whatever you want
   - Set the Identifier (audience) - note this value
   - Enable RBAC and Add Permissions in the Access Token (optional for role-based access)

3. Create a new Application in Auth0:
   - Choose "Regular Web Application" (not "Machine to Machine" or "Native")
   - In Settings, note the Domain, Client ID, and Client Secret
   - Add `http://localhost:8000/auth/callback` to Allowed Callback URLs
   - Add `http://localhost:8000` to Allowed Logout URLs
   - Add `http://localhost:8000` to Allowed Web Origins
   - Save changes

4. Set up Google as a Social Connection:
   - Go to Authentication > Social in the Auth0 dashboard
   - Set up Google OAuth credentials (follow Auth0's instructions)
   - Make sure Google connection is enabled for your application

5. Set up GitHub as a Social Connection:
   - Go to Authentication > Social in the Auth0 dashboard
   - Set up GitHub OAuth credentials:
     - Create a new OAuth App on GitHub (Settings > Developer settings > OAuth Apps)
     - Set the Authorization callback URL to `https://YOUR_AUTH0_DOMAIN/login/callback`
     - Copy the Client ID and Client Secret to Auth0
   - Make sure GitHub connection is enabled for your application

6. Enable Database Connection:
   - Go to Authentication > Database in the Auth0 dashboard
   - Create or enable a database connection
   - Enable it for your application
   - Create a test user or enable user signup

## Environment Variables

Create a `.env` file in the project root with the following variables:

```
AUTH0_DOMAIN=your-auth0-domain.auth0.com
AUTH0_CLIENT_ID=your-auth0-client-id
AUTH0_CLIENT_SECRET=your-auth0-client-secret
AUTH0_AUDIENCE=https://your-api-audience
API_URL=http://localhost:8000
SECRET_KEY=your-secret-key-for-sessions
DEBUG=True
```

## Setup

1. Install the required packages:
```bash
pip install -r requirements.txt
```

## Running the Application

To start the application, run:
```bash
python main.py
```

The application will be available at http://localhost:8000

## Authentication Flow

This application uses Auth0's Authorization Code flow which is the recommended approach for web applications:

1. User clicks on a login button (Auth0, Google, or GitHub)
2. User is redirected to Auth0's Universal Login page
3. User authenticates with their chosen method
4. Auth0 redirects back to your application with an authorization code
5. Your application exchanges the code for tokens
6. The user is now authenticated and can access protected routes

## Authentication Endpoints

- **Login Page**: `GET /auth/login`
  - Displays a simple page with login options

- **Auth0 Login**: `GET /auth/login/auth0`
  - Redirects to Auth0's Universal Login page
  - Handles username/password authentication
  - Callback URL: `/auth/callback`

- **Google OAuth Login**: `GET /auth/login/google`
  - Redirects to Google login page via Auth0
  - Callback URL: `/auth/callback`

- **GitHub OAuth Login**: `GET /auth/login/github`
  - Redirects to GitHub login page via Auth0
  - Callback URL: `/auth/callback`

- **User Profile**: `GET /auth/profile`
  - Requires authentication
  - Returns the authenticated user's profile

- **Logout**: `GET /auth/logout`
  - Clears session and redirects to Auth0 logout

## Protected Endpoints

- **Protected Data**: `GET /api/protected/data`
  - Requires authentication
  - Returns protected data

- **Admin Only**: `GET /api/protected/admin-only`
  - Requires authentication
  - In a real app, would check for admin permissions

## API Documentation

FastAPI automatically generates documentation for your API:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Authentication Mechanisms

This application uses two authentication mechanisms:

1. **Session-based Authentication**:
   - User authenticates with Auth0
   - Application stores user session data
   - Used for most web-based interactions

2. **JWT Token Authentication**:
   - Used for API authentication
   - Tokens are issued by Auth0 