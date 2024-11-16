import React, { useState } from 'react';
import { useRouter } from 'next/router';
import {
  Box,
  Container,
  Typography,
  Button,
  CircularProgress,
} from '@mui/material';
import { Add } from '@mui/icons-material';
import useSWR from 'swr';
import { toast } from 'react-hot-toast';

import { PodcastList } from '@/components/podcast/PodcastList';
import { CreatePodcastDialog } from '@/components/podcast/CreatePodcastDialog';
import { PodcastPlayer } from '@/components/podcast/PodcastPlayer';
import { podcastService } from '@/services/podcastService';
import { useAuth } from '@/hooks/useAuth';
import { Podcast, PodcastCreate } from '@/types/podcast';

const PodcastsPage = () => {
  const router = useRouter();
  const { id: searchSpaceId } = router.query;
  const { token } = useAuth();

  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedPodcast, setSelectedPodcast] = useState<Podcast | null>(null);
  const [playerOpen, setPlayerOpen] = useState(false);

  const { data: podcasts, mutate } = useSWR(
    token && searchSpaceId ? ['/podcasts', searchSpaceId, token] : null,
    () => podcastService.getSearchSpacePodcasts(Number(searchSpaceId), token!)
  );

  const handleCreate = async (data: PodcastCreate) => {
    try {
      await podcastService.createPodcast(Number(searchSpaceId), data, token!);
      mutate();
      toast.success('Podcast creation started');
    } catch (error) {
      toast.error('Failed to create podcast');
      console.error('Error creating podcast:', error);
    }
  };

  const handleDelete = async (podcast: Podcast) => {
    try {
      await podcastService.deletePodcast(Number(searchSpaceId), podcast.id, token!);
      mutate();
      toast.success('Podcast deleted');
    } catch (error) {
      toast.error('Failed to delete podcast');
      console.error('Error deleting podcast:', error);
    }
  };

  const handleDownload = async (podcast: Podcast) => {
    try {
      const blob = await podcastService.downloadPodcast(
        Number(searchSpaceId),
        podcast.id,
        token!
      );
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${podcast.title}.mp3`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      toast.error('Failed to download podcast');
      console.error('Error downloading podcast:', error);
    }
  };

  const handlePlay = (podcast: Podcast) => {
    setSelectedPodcast(podcast);
    setPlayerOpen(true);
  };

  if (!podcasts) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box my={4}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={4}>
          <Typography variant="h4">Podcasts</Typography>
          <Button
            variant="contained"
            color="primary"
            startIcon={<Add />}
            onClick={() => setCreateDialogOpen(true)}
          >
            Create Podcast
          </Button>
        </Box>

        <PodcastList
          podcasts={podcasts}
          onPlay={handlePlay}
          onDelete={handleDelete}
          onDownload={handleDownload}
        />

        <CreatePodcastDialog
          open={createDialogOpen}
          onClose={() => setCreateDialogOpen(false)}
          onCreate={handleCreate}
        />

        {selectedPodcast && (
          <PodcastPlayer
            podcast={selectedPodcast}
            open={playerOpen}
            onClose={() => {
              setPlayerOpen(false);
              setSelectedPodcast(null);
            }}
          />
        )}
      </Box>
    </Container>
  );
};

export default PodcastsPage;
