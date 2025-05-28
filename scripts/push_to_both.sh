#!/bin/bash

# MetaFunction - Push to Both Repositories Script
# This script pushes changes to both GitHub accounts

echo "🚀 Pushing MetaFunction to both repositories..."

# Push to sdodlapa account
echo "📤 Pushing to sdodlapa/MetaFunction..."
git push origin main

if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed to sdodlapa/MetaFunction"
else
    echo "❌ Failed to push to sdodlapa/MetaFunction"
    exit 1
fi

# Push to SanjeevaRDodlapati account
echo "📤 Pushing to SanjeevaRDodlapati/MetaFunction..."
git push sanjeeva main

if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed to SanjeevaRDodlapati/MetaFunction"
else
    echo "❌ Failed to push to SanjeevaRDodlapati/MetaFunction"
    exit 1
fi

echo "🎉 Successfully pushed to both repositories!"
echo "📍 sdodlapa: https://github.com/sdodlapa/MetaFunction"
echo "📍 SanjeevaRDodlapati: https://github.com/SanjeevaRDodlapati/MetaFunction"
