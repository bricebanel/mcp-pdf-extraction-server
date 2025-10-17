# Heroku Deployment Guide

## Files Created for Heroku

1. **Procfile** - Tells Heroku how to start the app
2. **requirements.txt** - Python dependencies
3. **runtime.txt** - Specifies Python version (3.12.7)
4. **Aptfile** - System dependencies (Tesseract OCR)
5. **setup.py** - Package installation configuration

## Heroku Configuration Steps

### 1. Add Buildpacks (IMPORTANT!)

In your Heroku dashboard or via CLI, you need to add TWO buildpacks:

**Via Heroku Dashboard:**
1. Go to your app: https://dashboard.heroku.com/apps/pdf-extraction-mcp-54041c60e7d7
2. Go to **Settings** tab
3. Scroll to **Buildpacks** section
4. Click **Add buildpack**
5. Add in this order:
   - First: `heroku-community/apt` (for Tesseract OCR)
   - Second: `heroku/python` (should be there already)

**Via Heroku CLI:**
```bash
heroku buildpacks:clear --app pdf-extraction-mcp-54041c60e7d7
heroku buildpacks:add --index 1 heroku-community/apt --app pdf-extraction-mcp-54041c60e7d7
heroku buildpacks:add --index 2 heroku/python --app pdf-extraction-mcp-54041c60e7d7
```

### 2. Push Changes to GitHub

Commit and push all the new files:
```bash
git add Procfile requirements.txt runtime.txt Aptfile setup.py HEROKU_DEPLOY.md
git commit -m "Add Heroku deployment configuration"
git push origin main
```

### 3. Trigger Deployment

Since your Heroku app is connected to GitHub with automatic deploys:
- The push will automatically trigger a new deployment
- Watch the build logs in Heroku dashboard under **Activity** tab

### 4. Verify Deployment

After deployment completes:
- Check the logs: `heroku logs --tail --app pdf-extraction-mcp-54041c60e7d7`
- Test the MCP endpoint: https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp

## Troubleshooting

### If you see "Application Error"
- Check logs: `heroku logs --tail --app pdf-extraction-mcp-54041c60e7d7`
- Common issues:
  - Missing buildpacks (apt buildpack is crucial for Tesseract)
  - Wrong Python version in runtime.txt
  - Package installation failures

### If Tesseract is not found
- Verify apt buildpack is installed BEFORE python buildpack
- Check that Aptfile exists and contains tesseract-ocr

### Check Build Status
```bash
heroku releases --app pdf-extraction-mcp-54041c60e7d7
```

## Your MCP Server URLs

Once deployed:
- **MCP Endpoint**: https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp
- **SSE Endpoint**: https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/sse
- **Messages Endpoint**: https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/messages/

## Environment Variables (if needed)

You can set environment variables in Heroku:
```bash
heroku config:set VARIABLE_NAME=value --app pdf-extraction-mcp-54041c60e7d7
```

## Logs

View real-time logs:
```bash
heroku logs --tail --app pdf-extraction-mcp-54041c60e7d7
```
