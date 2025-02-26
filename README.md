# Microsoft Onedrive with python web ui

**Setup Instructions:**

1. Create Azure AD Application:
   - Go to Azure Portal → App Registrations → New Registration
   - Set redirect URI to `http://localhost:8000/callback`
   - Add client secret and note down CLIENT_ID & CLIENT_SECRET

2. Install requirements:
```bash
pip install gradio msal python-dotenv requests msgraph-sdk
```

3. Create `.env` file:
```
CLIENT_ID=your_azure_client_id
CLIENT_SECRET=your_azure_client_secret
```

**Features:**
- Modern Gradio interface with emoji icons
- File/folder navigation with breadcrumbs
- Upload/download functionality
- Folder creation/delete operations
- Responsive design with theme support
- Secure token management
- Real-time updates

---

Key Improvements and Integrations:

1. **Hybrid Architecture**
- Combines REST API direct calls (from reference code) with OOP wrapper class
- Maintains SDK-like convenience while keeping transparency of API operations

2. **Enhanced Authentication Flow**
- Interactive authentication sequence with automatic token refresh
- Secure state management instead of global variables
- Complete OAuth 2.0 code flow with PKCE support

3. **Modern UI Features**
- Hybrid tabbed/navigation interface combining both approaches
- Visual folder breadcrumbs
- Interactive file tree with type icons
- Multiple file upload support

4. **Improved Error Handling**
- Automatic token refresh on 401 errors
- Detailed operation logging
- Visual feedback for all actions

5. **Advanced Features**
- Full folder navigation history with stack
- Type-safe API request handler
- Multi-threaded upload capability
- Responsive layout with collapsible panels

6. **Security Enhancements**
- Secure token storage in session state
- Environment variable configuration
- No persistent credential storage

7. **Extended Operations**
- Drag-and-drop file upload
- Batch operations
- Contextual navigation
- Detailed metadata display

To use this improved version:

1. Install requirements:
```bash
pip install gradio requests msal python-dotenv
python onedrive_gradio_r1-v2.py
```

2. Configure Azure AD app with:
- Redirect URI: `http://localhost:8000/callback`
- API permissions: Files.ReadWrite.All, User.Read, offline_access

3. Create `.env` file with your credentials:
```
CLIENT_ID=your_app_id
CLIENT_SECRET=your_app_secret
```

This implementation combines the structured approach of the original code with the explicit API control of the reference code while adding modern UI elements and robust error handling.
