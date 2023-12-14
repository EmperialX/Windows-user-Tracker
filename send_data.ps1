$flaskApiUrl = "http://127.0.0.1:5000/connect"
while ($true) {
    Invoke-RestMethod -Uri $flaskApiUrl -Method Post
    Start-Sleep -Seconds 5
}
