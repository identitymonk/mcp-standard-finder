#!/usr/bin/env python3
"""
Test script for IETF Mail Archive parsing
Fetches actual data to understand HTML structure and test parsing
"""

import urllib.request
import re
import sys
import asyncio

# Add parent directory to path
sys.path.insert(0, '.')

def fetch_url(url: str) -> str:
    """Fetch URL content"""
    print(f"Fetching: {url}")
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (compatible; MCP-Standards-Finder/1.0)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            }
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8', errors='replace')
            print(f"Fetched {len(content)} bytes")
            return content
    except Exception as e:
        print(f"Error: {e}")
        return ""

def test_browse_endpoint():
    """Test the browse endpoint for a mailing list"""
    print("\n" + "=" * 60)
    print("TEST 1: Browse endpoint (wimse mailing list)")
    print("=" * 60)
    
    url = "https://mailarchive.ietf.org/arch/browse/wimse/"
    html = fetch_url(url)
    
    if not html:
        print("Failed to fetch browse page")
        return
    
    # Save HTML for inspection
    with open("output/browse_wimse.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Saved to output/browse_wimse.html")
    
    # Look for message patterns
    print("\n--- Looking for message patterns ---")
    
    # Check for xtr class (table rows)
    xtr_count = len(re.findall(r'class="xtr"', html))
    print(f"Found {xtr_count} elements with class='xtr'")
    
    # Check for xtd class (table cells)
    xtd_count = len(re.findall(r'class="xtd', html))
    print(f"Found {xtd_count} elements with class='xtd'")
    
    # Check for msg-detail links
    msg_detail_count = len(re.findall(r'class="msg-detail"', html))
    print(f"Found {msg_detail_count} elements with class='msg-detail'")
    
    # Check for /arch/msg/ links
    arch_msg_links = re.findall(r'href="(/arch/msg/[^"]+)"', html)
    print(f"Found {len(arch_msg_links)} /arch/msg/ links")
    if arch_msg_links[:3]:
        print("Sample links:")
        for link in arch_msg_links[:3]:
            print(f"  {link}")

def test_message_page():
    """Test fetching a specific message page"""
    print("\n" + "=" * 60)
    print("TEST 2: Message page")
    print("=" * 60)
    
    # First get a message URL from browse
    browse_url = "https://mailarchive.ietf.org/arch/browse/wimse/"
    html = fetch_url(browse_url)
    
    if not html:
        print("Failed to fetch browse page")
        return
    
    # Find first message link
    msg_links = re.findall(r'href="(/arch/msg/wimse/[^"]+)"', html)
    if not msg_links:
        print("No message links found")
        return
    
    msg_url = f"https://mailarchive.ietf.org{msg_links[0]}"
    print(f"\nFetching message: {msg_url}")
    
    msg_html = fetch_url(msg_url)
    if not msg_html:
        print("Failed to fetch message")
        return
    
    # Save for inspection
    with open("output/message_sample.html", "w", encoding="utf-8") as f:
        f.write(msg_html)
    print("Saved to output/message_sample.html")
    
    # Look for message structure
    print("\n--- Message structure analysis ---")
    
    # Check for msg-body
    msg_body = re.search(r'id="msg-body"', msg_html)
    print(f"msg-body found: {bool(msg_body)}")
    
    # Check for msg-from
    msg_from = re.search(r'id="msg-from"', msg_html)
    print(f"msg-from found: {bool(msg_from)}")
    
    # Check for msg-date
    msg_date = re.search(r'id="msg-date"', msg_html)
    print(f"msg-date found: {bool(msg_date)}")
    
    # Extract actual values
    print("\n--- Extracted values ---")
    
    # Subject from title
    title_match = re.search(r'<title>([^<]+)</title>', msg_html, re.IGNORECASE)
    if title_match:
        print(f"Title: {title_match.group(1)[:80]}")
    
    # From
    from_match = re.search(r'<span id="msg-from"[^>]*>([^<]+)</span>', msg_html, re.IGNORECASE)
    if from_match:
        print(f"From: {from_match.group(1)[:80]}")
    
    # Date
    date_match = re.search(r'<span id="msg-date"[^>]*>([^<]+)</span>', msg_html, re.IGNORECASE)
    if date_match:
        print(f"Date: {date_match.group(1)}")

async def test_mail_archive_service():
    """Test the SimpleMailArchiveService class"""
    print("\n" + "=" * 60)
    print("TEST 3: SimpleMailArchiveService parsing")
    print("=" * 60)
    
    try:
        from standard_finder import SimpleMailArchiveService
        
        service = SimpleMailArchiveService()
        
        # Test search
        print("\n--- Testing search_mail_archive ---")
        results = await service.search_mail_archive("wimse", mailing_list="wimse", limit=5)
        
        print(f"Found {len(results)} results")
        for i, result in enumerate(results[:5], 1):
            print(f"\n{i}. {result['subject'][:60]}...")
            print(f"   Author: {result['author']}")
            print(f"   Date: {result['date']}")
            print(f"   List: {result['mailing_list']}")
            print(f"   URL: {result['url']}")
        
        # Test get_message if we have results
        if results:
            print("\n--- Testing get_message ---")
            msg = await service.get_message(results[0]['url'])
            print(f"Subject: {msg['subject'][:60]}...")
            print(f"Author: {msg['author'][:60]}...")
            print(f"Date: {msg['date']}")
            print(f"Content preview: {msg['content'][:200]}...")
        
        print("\n✅ SimpleMailArchiveService tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run all tests"""
    print("IETF Mail Archive HTML Structure Analysis")
    print("=" * 60)
    
    test_browse_endpoint()
    test_message_page()
    
    # Run async test
    asyncio.run(test_mail_archive_service())
    
    print("\n" + "=" * 60)
    print("Analysis complete. Check output/ folder for HTML files.")
    print("=" * 60)

if __name__ == "__main__":
    main()
