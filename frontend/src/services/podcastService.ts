import axios from 'axios';
import { Podcast, PodcastCreate, PodcastUpdate } from '@/types/podcast';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const podcastService = {
  async createPodcast(searchSpaceId: number, data: PodcastCreate, token: string): Promise<Podcast> {
    const response = await axios.post(
      `${API_URL}/searchspace/${searchSpaceId}/podcasts/`,
      data,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },

  async getSearchSpacePodcasts(searchSpaceId: number, token: string): Promise<Podcast[]> {
    const response = await axios.get(
      `${API_URL}/searchspace/${searchSpaceId}/podcasts/`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },

  async getPodcast(searchSpaceId: number, podcastId: number, token: string): Promise<Podcast> {
    const response = await axios.get(
      `${API_URL}/searchspace/${searchSpaceId}/podcasts/${podcastId}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },

  async updatePodcast(
    searchSpaceId: number,
    podcastId: number,
    data: PodcastUpdate,
    token: string
  ): Promise<Podcast> {
    const response = await axios.put(
      `${API_URL}/searchspace/${searchSpaceId}/podcasts/${podcastId}`,
      data,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
    return response.data;
  },

  async deletePodcast(searchSpaceId: number, podcastId: number, token: string): Promise<void> {
    await axios.delete(
      `${API_URL}/searchspace/${searchSpaceId}/podcasts/${podcastId}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );
  },

  async downloadPodcast(searchSpaceId: number, podcastId: number, token: string): Promise<Blob> {
    const response = await axios.get(
      `${API_URL}/searchspace/${searchSpaceId}/podcasts/${podcastId}/download`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        responseType: 'blob',
      }
    );
    return response.data;
  },
};
