#!/usr/bin/env python3
"""
Test script to validate scraper functionality before full implementation.
Run this to test Reddit and News scraping independently.
"""

import requests
import feedparser
import time
import json
from datetime import datetime


def test_reddit_json():
    """Test 1 - Basic Reddit JSON endpoint access"""
    print("\n" + "=" * 60)
    print("TEST 1: Reddit JSON Endpoint Access")
    print("=" * 60)

    url = "https://www.reddit.com/r/dogs/top.json?t=day&limit=25"
    headers = {'User-Agent': 'CanadianPetPulse/0.1.0 (Educational Project)'}

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            posts = data['data']['children']
            print(f"✓ Retrieved {len(posts)} posts from r/dogs")

            # Inspect first post structure
            if posts:
                sample = posts[0]['data']
                print(f"\nSample Post:")
                print(f"  Title: {sample['title'][:60]}...")
                print(f"  Score: {sample['score']}")
                print(f"  Comments: {sample['num_comments']}")
                print(f"  Created: {datetime.fromtimestamp(sample['created_utc'])}")
                print(f"  URL: {sample['url'][:60]}...")

                # Check for all required fields
                required_fields = ['id', 'title', 'score', 'num_comments', 'created_utc',
                                   'url', 'permalink', 'subreddit', 'author']
                missing = [f for f in required_fields if f not in sample]

                if missing:
                    print(f"✗ Missing fields: {missing}")
                else:
                    print(f"✓ All required fields present")

            return True
        else:
            print(f"✗ Failed with status {response.status_code}")
            return False

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_multiple_subreddits():
    """Test 2 - Multi-subreddit scraping with rate limiting"""
    print("\n" + "=" * 60)
    print("TEST 2: Multi-Subreddit Scraping")
    print("=" * 60)

    subreddits = ['dogs', 'puppy101', 'toronto', 'vancouver']
    headers = {'User-Agent': 'CanadianPetPulse/0.1.0 (Educational Project)'}

    results = {}

    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/top.json?t=day&limit=10"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                post_count = len(data['data']['children'])
                results[sub] = post_count
                print(f"✓ r/{sub}: {post_count} posts")
            else:
                results[sub] = 0
                print(f"✗ r/{sub}: Failed (status {response.status_code})")

            # Rate limiting - wait 2 seconds between requests
            if sub != subreddits[-1]:  # Don't wait after last one
                print(f"  Waiting 2 seconds (rate limiting)...")
                time.sleep(2)

        except Exception as e:
            results[sub] = 0
            print(f"✗ r/{sub}: Error - {e}")

    total = sum(results.values())
    print(f"\nTotal posts retrieved: {total}")
    return total > 0


def test_rss_feeds():
    """Test 3 - RSS feed parsing"""
    print("\n" + "=" * 60)
    print("TEST 3: RSS Feed Access")
    print("=" * 60)

    feeds = {
        'CBC Canada': 'https://www.cbc.ca/webfeed/rss/rss-canada',
        'CTV News': 'https://www.ctvnews.ca/rss/ctvnews-ca-top-stories-public-rss-1.822009',
        'Global News': 'https://globalnews.ca/feed/',
    }

    results = {}

    for source, url in feeds.items():
        try:
            feed = feedparser.parse(url)

            if feed.entries:
                entry_count = len(feed.entries)
                results[source] = entry_count
                print(f"✓ {source}: {entry_count} entries")
                print(f"  Feed Title: {feed.feed.get('title', 'N/A')}")

                # Show first entry
                if feed.entries:
                    first = feed.entries[0]
                    print(f"  Sample: {first.title[:60]}...")
            else:
                results[source] = 0
                print(f"✗ {source}: No entries found")

        except Exception as e:
            results[source] = 0
            print(f"✗ {source}: Error - {e}")

    total = sum(results.values())
    print(f"\nTotal articles retrieved: {total}")
    return total > 0


def test_pet_filtering():
    """Test 4 - Pet keyword filtering on news"""
    print("\n" + "=" * 60)
    print("TEST 4: Pet Content Filtering")
    print("=" * 60)

    pet_keywords = ['dog', 'cat', 'pet', 'puppy', 'kitten', 'animal', 'veterinary', 'vet']

    try:
        feed = feedparser.parse('https://www.cbc.ca/webfeed/rss/rss-canada')

        pet_stories = []
        for entry in feed.entries:
            title_lower = entry.title.lower()
            summary_lower = entry.get('summary', '').lower()

            if any(keyword in title_lower or keyword in summary_lower
                   for keyword in pet_keywords):
                pet_stories.append(entry.title)

        print(f"Total entries: {len(feed.entries)}")
        print(f"Pet-related stories: {len(pet_stories)}")

        if pet_stories:
            print(f"\nPet stories found:")
            for i, story in enumerate(pet_stories[:5], 1):
                print(f"  {i}. {story}")

            if len(pet_stories) > 5:
                print(f"  ... and {len(pet_stories) - 5} more")

        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_canadian_detection():
    """Test 5 - Canadian relevance detection"""
    print("\n" + "=" * 60)
    print("TEST 5: Canadian Relevance Detection")
    print("=" * 60)

    test_cases = [
        ("My dog loves Toronto parks!", True),
        ("Best vet in Vancouver BC", True),
        ("Puppy training tips", False),
        ("Montreal dog rescue needs help", True),
        ("Canadian pet food regulations", True),
        ("Walking my dog in Calgary", True),
        ("General training advice", False),
        ("Ottawa animal shelter", True),
    ]

    canadian_keywords = [
        'toronto', 'vancouver', 'montreal', 'calgary', 'ottawa',
        'edmonton', 'winnipeg', 'canadian', 'canada', 'bc', 'ontario',
        'quebec', 'alberta'
    ]

    correct = 0
    total = len(test_cases)

    for text, expected in test_cases:
        is_canadian = any(kw in text.lower() for kw in canadian_keywords)
        status = "✓" if is_canadian == expected else "✗"

        if is_canadian == expected:
            correct += 1

        print(f"{status} {text} -> {'Canadian' if is_canadian else 'Not Canadian'}")

    accuracy = (correct / total) * 100
    print(f"\nAccuracy: {correct}/{total} ({accuracy:.1f}%)")

    return accuracy >= 80


def main():
    """Run all validation tests"""
    print("\n" + "=" * 60)
    print("CANADIAN PET PULSE - SCRAPER VALIDATION TESTS")
    print("=" * 60)

    tests = [
        ("Reddit JSON Access", test_reddit_json),
        ("Multi-Subreddit Scraping", test_multiple_subreddits),
        ("RSS Feed Parsing", test_rss_feeds),
        ("Pet Content Filtering", test_pet_filtering),
        ("Canadian Detection", test_canadian_detection),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n✗ {test_name} failed with exception: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")

    passed_count = sum(results.values())
    total_count = len(results)

    print(f"\nOverall: {passed_count}/{total_count} tests passed")

    if passed_count == total_count:
        print("\n🎉 All tests passed! Ready to implement scrapers.")
    elif passed_count >= 3:
        print("\n⚠️  Most tests passed. Review failures before proceeding.")
    else:
        print("\n❌ Multiple tests failed. Fix issues before proceeding.")


if __name__ == '__main__':
    main()
