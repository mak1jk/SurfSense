export interface Podcast {
  id: number;
  title: string;
  content: string;
  status: string;
  is_completed: boolean;
  file_location?: string;
  created_at: string;
}

export interface PodcastCreate {
  title: string;
  content: string;
  word_count: number;
}

export interface PodcastUpdate {
  title?: string;
  content?: string;
  status?: string;
  is_completed?: boolean;
}
