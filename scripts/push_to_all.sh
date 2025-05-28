#!/bin/bash

# MetaFunction - Push to All Repositories Script
# This script pushes changes to all three GitHub accounts

echo "🚀 Pushing MetaFunction to all repositories..."

# Push to sdodlapa account (primary)
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

# Push to sdodlapati3 account
echo "📤 Pushing to sdodlapati3/MetaFunction..."
git push sdodlapati3 main

if [ $? -eq 0 ]; then
    echo "✅ Successfully pushed to sdodlapati3/MetaFunction"
else
    echo "❌ Failed to push to sdodlapati3/MetaFunction"
    exit 1
fi

echo "🎉 Successfully pushed to all three repositories!"
echo "📍 sdodlapa: https://github.com/sdodlapa/MetaFunction"
echo "📍 SanjeevaRDodlapati: https://github.com/SanjeevaRDodlapati/MetaFunction"
echo "📍 sdodlapati3: https://github.com/sdodlapati3/MetaFunction"
