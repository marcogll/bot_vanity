# Coolify Deployment Guide

This guide will help you deploy Vanessa Bot to Coolify.

## Prerequisites

- A Coolify instance (self-hosted or cloud)
- A GitHub repository with the code (already pushed to `git@github.com:marcogll/bot_vanity.git`)
- Evolution API credentials
- OpenAI API key
- Evolution API instance configured

## Step-by-Step Deployment

### Option 1: Git Repository (Recommended)

#### 1. Create Project in Coolify

1. Log in to your Coolify dashboard
2. Click "New Project"
3. Enter project name: `vanessa-bot`
4. Click "Create"

#### 2. Configure Git Source

1. Click "New Service" in your project
2. Select "Git Repository"
3. Configure:
   - **Repository URL:** `git@github.com:marcogll/bot_vanity.git`
   - **Branch:** `main`
   - **Buildpack:** Node.js
4. Click "Next"

#### 3. Configure Build Settings

In the "Build" section:
```
Build Command: npm run build
Output Directory: dist
Start Command: npm start
```

#### 4. Configure Environment Variables

In the "Environment" section, add these variables:

**Important:** Set `NODE_ENV` as "Runtime only" (NOT available at build time). This allows the build stage to install devDependencies (like TypeScript) needed for compilation.

```env
NODE_ENV=production  (Runtime only, NOT available at build time)
PORT=3000
EVOLUTION_API_URL=https://evolution.soul23.cloud/manager/
EVOLUTION_API_KEY=your_actual_evolution_api_key
EVOLUTION_INSTANCE=noire
OPENAI_API_KEY=your_actual_openai_api_key
OPENAI_MODEL=gpt-4o-mini
FORMBRICKS_URL=https://your-formbricks-instance.com/form/quejas
```

**Important:** Replace `your_actual_evolution_api_key` and `your_actual_openai_api_key` with your real keys.

**Note on NODE_ENV:** If Coolify warns about NODE_ENV being set to "development" at build time, this is expected and OK. The Dockerfile uses a multi-stage build that installs all dependencies during the build stage (including TypeScript), and only production dependencies at runtime.

#### 5. Configure Port

In the "Network" section:
- **Port:** `3000`

#### 6. Deploy

Click "Deploy" and wait for the build to complete.

### Option 2: Docker Compose

#### 1. Create Project in Coolify

Same as Option 1.

#### 2. Configure Docker Compose Source

1. Click "New Service" in your project
2. Select "Docker Compose"
3. Paste the content of `docker-compose.yml`
4. Click "Next"

#### 3. Configure Environment Variables

Same as Option 1, add all environment variables.

#### 4. Deploy

Click "Deploy".

## Post-Deployment Steps

### 1. Get Your Application URL

After deployment, Coolify will provide a URL like:
- `https://vanessa-bot.your-coolify-domain.com`
- Or your custom domain if configured

### 2. Configure Evolution API Webhook

1. Log in to your Evolution API instance
2. Navigate to your instance settings
3. Configure webhook:
   - **URL:** `https://vanessa-bot.your-coolify-domain.com/webhook`
   - **Method:** POST
   - **Content-Type:** `application/json`
4. Save configuration

### 3. Test the Deployment

#### Test Health Endpoint
```bash
curl https://vanessa-bot.your-coolify-domain.com/health
```

Expected response:
```json
{"status":"healthy","timestamp":"2026-02-07T21:00:00.000Z"}
```

#### Test Stats Endpoint
```bash
curl https://vanessa-bot.your-coolify-domain.com/stats
```

#### Test Bot with Test Endpoint
```bash
curl -X POST https://vanessa-bot.your-coolify-domain.com/test \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola, ¿qué servicios tienen?",
    "phoneNumber": "test_123",
    "pushName": "María"
  }'
```

### 4. Monitor Logs

In Coolify dashboard:
1. Go to your service
2. Click "Logs"
3. View real-time logs from your application

## Troubleshooting

### Build Fails

1. Check if Node.js version is compatible (20+)
2. Check if all dependencies are in `package.json`
3. View build logs for specific errors

### Application Won't Start

1. Check environment variables are correctly set
2. Check if port 3000 is available
3. View application logs in Coolify dashboard

### Webhook Not Working

1. Check if webhook URL is correct
2. Check if Evolution API can reach your Coolify instance
3. Check if webhook is receiving traffic in logs
4. Test webhook manually with curl

### OpenAI API Errors

1. Verify OPENAI_API_KEY is correct
2. Check if you have credits in your OpenAI account
3. Check if the model `gpt-4o-mini` is available

## Monitoring

### Health Check

The application includes a health check that runs every 30 seconds. You can monitor this in Coolify dashboard under "Health Check" section.

### Logs

View logs in real-time in Coolify dashboard or use the CLI:
```bash
coolify logs vanessa-bot
```

### Statistics

View memory and conversation statistics:
```bash
curl https://vanessa-bot.your-coolify-domain.com/stats
```

## Scaling

If you need to handle more traffic, you can:

1. **Scale horizontally:** Increase the number of replicas in Coolify
2. **Add Redis:** Modify the code to use Redis for persistent memory
3. **Add load balancer:** Coolify can automatically load balance between replicas

## Security Best Practices

1. **Never commit .env files:** Use environment variables in Coolify
2. **Use HTTPS:** Enable SSL in Coolify settings
3. **Limit access:** Configure firewall rules in Coolify
4. **Regular updates:** Keep dependencies updated
5. **Monitor logs:** Regularly check for suspicious activity

## Backup

The application uses in-memory storage by default. For production:
1. **Add Redis:** Configure Redis for persistent storage
2. **Enable backups:** Coolify supports automatic backups
3. **Export data:** Regularly export conversation data for analysis

## Support

If you encounter issues:
1. Check the logs in Coolify dashboard
2. Review this guide's troubleshooting section
3. Check the main README.md for additional information
4. Open an issue on GitHub: `https://github.com/marcogll/bot_vanity/issues`
