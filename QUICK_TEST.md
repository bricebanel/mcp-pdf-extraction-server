# Quick Test Reference

## TL;DR - Run This After Deploying

```bash
# 1. Deploy (do this yourself via git push)
git add .
git commit -m "Add testing infrastructure"
git push origin master

# 2. Wait 30 seconds for deployment

# 3. Quick health check
curl https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/health

# 4. Run full test (20 attempts)
python test_mcp_client.py https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/mcp 20

# 5. Watch logs in another terminal
heroku logs --tail --app pdf-extraction-mcp-54041c60e7d7

# 6. Check metrics
curl https://pdf-extraction-mcp-54041c60e7d7.herokuapp.com/metrics
```

## What to Look For

### ✅ Good Signs (Server Working)
- Test success rate: 100% or >98%
- Logs show: `✓ Extraction successful`
- Metrics show: `"success_rate": "100%"`
- Memory stays below 300 MB

### ⚠️ Bad Signs (Server Issues)
- Test success rate: <95%
- Pattern: "Every other request fails"
- Logs show repeated errors
- Memory >400 MB (approaching limit)

### 🔍 Diagnosis

| Test Result | Forest Admin Result | Conclusion |
|-------------|---------------------|------------|
| ✓ Pass      | ✗ Fail              | **Forest Admin issue** |
| ✗ Fail      | ✗ Fail              | **Server issue** |
| ✓ Pass      | ✓ Pass              | **No issue** (intermittent?) |

## If Test Fails

1. Check logs for error messages
2. Run `curl .../metrics` to check resources
3. Try testing with smaller PDFs
4. Check if it's a pattern (every 2nd, 3rd, etc.)

## If Test Passes But Forest Admin Fails

Forest Admin client issues to check:
- Are they reusing SSE connections properly?
- Are they sending requests too fast?
- Are they handling session IDs correctly?
- Report to Forest Admin with test results showing server works

## Files to Share When Reporting Issues

```bash
# Save test output
python test_mcp_client.py ... > test_results.txt 2>&1

# Save metrics
curl .../metrics > metrics.json

# Save logs
heroku logs --tail > logs.txt
```
