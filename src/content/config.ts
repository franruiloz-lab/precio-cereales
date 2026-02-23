import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    title: z.string(),
    description: z.string(),
    date: z.string(),
    lastUpdated: z.string().optional(),
    category: z.string(),
    tags: z.array(z.string()),
    readingTime: z.string(),
  }),
});

export const collections = { blog };
