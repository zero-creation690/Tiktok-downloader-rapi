import axios from 'axios';

// IMPORTANT: Next.js API Routes have a max request body size. 
// We disable the default body parser to handle the video stream directly.
export const config = {
  api: {
    bodyParser: false,
    // Set maxDuration for longer downloads (default is 10s on Hobby/Pro)
    // You may need to increase this in vercel.json for long videos
    // maxDuration: 60, 
  },
};

/**
 * Handles the video download API request.
 * The endpoint will be accessed at /api/download
 */
export default async function handler(req, res) {
  // Only allow POST requests
  if (req.method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    return res.status(405).end(`Method ${req.method} Not Allowed`);
  }

  // Next.js body parser is disabled, so we manually parse the URL from the request body
  let tiktokUrl;
  try {
    const data = await new Promise((resolve) => {
      let body = '';
      req.on('data', chunk => {
        body += chunk.toString();
      });
      req.on('end', () => {
        resolve(JSON.parse(body));
      });
    });
    tiktokUrl = data.url;
  } catch (error) {
    return res.status(400).json({ error: 'Invalid JSON body or missing URL.' });
  }

  if (!tiktokUrl) {
    return res.status(400).json({ error: 'Missing TikTok video URL.' });
  }

  // --- ⚠️ CORE LOGIC: REPLACE THIS SECTION ⚠️ ---
  // You must replace this placeholder with logic to find the DIRECT VIDEO URL.
  // This is the hardest part and must be done using a stable third-party API 
  // or a sophisticated, up-to-date scraping library which can be very unstable.

  let directVideoUrl;
  try {
    // 1. Fetch data from your scraping service/library
    // Example using a placeholder function (YOU NEED TO IMPLEMENT THIS)
    // const scraperResponse = await getDirectTikTokLink(tiktokUrl);
    // directVideoUrl = scraperResponse.video_url;

    // FOR DEMO: Let's use a public domain video link to show the streaming works
    // In a real app, this is where your scraper or API result would go.
    directVideoUrl = 'https://sample-videos.com/video123/mp4/720/big_buck_bunny_720p_10mb.mp4';
    
  } catch (error) {
    console.error('Video link extraction failed:', error);
    return res.status(500).json({ error: 'Could not extract direct video link. Service might be down.' });
  }
  // --------------------------------------------------


  try {
    // 2. Stream the video file from the direct URL
    const videoResponse = await axios.get(directVideoUrl, {
      responseType: 'stream',
      // Add a timeout in case the video server is slow
      timeout: 15000 
    });

    // 3. Set download headers for the browser
    const filename = `tiktok-video-${Date.now()}.mp4`;

    res.setHeader('Content-Type', 'video/mp4');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}"`);
    // Pass headers from the external video server if needed (e.g., Content-Length)
    if (videoResponse.headers['content-length']) {
      res.setHeader('Content-Length', videoResponse.headers['content-length']);
    }

    // 4. Pipe the video stream directly to the Vercel response
    videoResponse.data.pipe(res);

    // Wait for the stream to finish
    await new Promise((resolve, reject) => {
      videoResponse.data.on('end', resolve);
      videoResponse.data.on('error', reject);
      res.on('error', reject);
    });

  } catch (error) {
    console.error('Video streaming failed:', error.message);
    // Ensure the response is ended if an error occurs during streaming
    if (!res.headersSent) {
      return res.status(500).json({ error: 'Failed to stream video file.' });
    }
  }
}
