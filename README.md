# Coffee Order Notification Server

A Flask server that receives order notifications from Firebase Cloud Functions and triggers coffee machine operations.

## Features

- Receives HTTP notifications from Firebase
- Secure API key authentication
- Rate limiting protection
- Health check endpoint
- Test endpoint for connectivity

## Endpoints

- `GET /health` - Health check
- `POST /order-notification` - Process coffee orders
- `POST /test` - Test connectivity

## Environment Variables

- `API_KEY` - Secret key for authentication
- `PORT` - Server port (set automatically by Railway)

## Deployment

This server is designed to run on Railway for secure, reliable operation. 