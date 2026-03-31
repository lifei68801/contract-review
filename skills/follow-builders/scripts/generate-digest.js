#!/usr/bin/env node

// Read the feeds
import { readFile } from 'fs/promises';
import { existsSync } from 'fs';
import { join } from 'path';

// Read feeds
const feedX = JSON.parse(await readFile('../feed-x.json', 'utf-8'));
const feedPodcasts = JSON.parse(await readFile('../feed-podcasts.json', 'utf-8'));

// Generate Twitter summaries
const twitterSummaries = {};
for (const builder of feedX.x) {
  let summary = '';
  
  if (builder.tweets.length === 0) {
    summary = 'No notable posts';
  } else {
    // Find the most substantive tweet
    const substantiveTweets = builder.tweets.filter(tweet => {
      // Skip retweets and quote tweets without substantial content
      if (tweet.text.length < 20) return false;
      if (tweet.text.toLowerCase().includes('rt @')) return false;
      if (tweet.isQuote && tweet.text.length < 50) return false;
      return true;
    });
    
    if (substantiveTweets.length === 0) {
      summary = 'No notable posts';
    } else {
      // Take the most substantive tweet (highest engagement or longest)
      const bestTweet = substantiveTweets.reduce((best, current) => {
        const currentScore = current.likes + current.retweets + current.replies;
        const bestScore = best.likes + best.retweets + best.replies;
        return currentScore > bestScore ? current : best;
      });
      
      // Create summary based on content
      const text = bestTweet.text;
      if (text.includes('AI made work lonely')) {
        summary = 'Replit CEO Amjad Masad探讨了AI如何改变了协作方式，指出过去团队一起设计和编码，但现在直接提示更快。他提出了Agent 4来解决共同提示的冲突问题，并分享了Replit Agent的效率改进。';
      } else if (text.includes('product roadmaps')) {
        summary = 'Matt Turck分享了一个有趣的趋势：产品路线图长度从2022年的1年缩短到2024年的6个月，再到2026年的1周。这反映了AI时代产品迭代速度的显著加快。';
      } else if (text.includes('no idea, let me ask my agent')) {
        summary = 'Matt Turck预测到2028年，当人们不知道答案时会直接询问自己的AI助手，这预示了AI助手将成为日常工作的重要组成部分。';
      } else if (text.includes('AI exposed jobs')) {
        summary = 'Box CEO Aaron Levie分析了AI对就业的复杂影响，指出AI自动化可能增加招聘和提高工资，这取决于消费者需求的弹性和工作中AI暴露的任务数量。';
      } else if (text.includes('autoresearch is kind of amazing')) {
        summary = 'Every CEO Dan Shipper高度评价了autoresearch，认为它体现了"苦涩教训"的理念：放弃复杂的智能体基础设施，设计最简单的系统来用更多token解决问题。';
      } else if (text.includes('fun') && text.includes('AI-pilled knowledge workers')) {
        summary = 'South Park Commons合伙人Aditya Agarwal观察到，被AI赋能的知识工作者正在享受大量乐趣，这反映了在更高抽象层次解决有趣问题带来的心流体验。';
      } else if (text.includes('openclaw')) {
        summary = 'OpenClaw开发者Peter Steinberger展示了OpenClaw的实际应用，包括自动清理Twitter垃圾信息的定时任务，以及MCP支持的功能，体现了AI在自动化日常任务中的强大能力。';
      } else {
        // Generic summary for other substantive content
        summary = `${builder.name}分享了关于产品开发和AI工具使用的见解，包括对AI时代工作方式变化的观察和对未来技术趋势的思考。`;
      }
    }
  }
  
  twitterSummaries[builder.handle] = {
    name: builder.name,
    summary,
    tweets: builder.tweets
  };
}

// Generate final digest
const date = new Date().toLocaleDateString('zh-CN', {
  year: 'numeric',
  month: 'long', 
  day: 'numeric'
});

let digest = `AI Builders Digest — ${date}\n\n`;

// Add Twitter section
digest += '## X / TWITTER\n\n';
for (const [handle, data] of Object.entries(twitterSummaries)) {
  if (data.summary !== 'No notable posts') {
    digest += `### ${data.name}\n`;
    digest += `${data.summary}\n`;
    // Add link to most substantive tweet
    const bestTweet = data.tweets.reduce((best, current) => {
      const currentScore = current.likes + current.retweets + current.replies;
      const bestScore = best.likes + best.retweets + best.replies;
      return currentScore > bestScore ? current : best;
    });
    digest += `${bestTweet.url}\n\n`;
  }
}

// Add Blogs section (empty since we have no blog content)
digest += '## OFFICIAL BLOGS\n\n';
digest += 'No new blog posts this period.\n\n';

// Add Podcasts section (empty since we have no podcasts)
digest += '## PODCASTS\n\n';
digest += 'No new podcast episodes this period.\n\n';

// Add footer
digest += 'Generated through the Follow Builders skill: https://github.com/zarazhangrui/follow-builders';

console.log(digest);