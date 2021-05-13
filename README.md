Rebuild Docker Locally:
docker stop slurp-bot
docker rm slurp-bot
docker rmi slurp-bot
docker build --tag slurp-bot .

Run App Locally:
docker run -p 5000:5000 --name slurp-bot -e PORT=5000 slurp-bot

Deploy to Heroku:
git push heroku main