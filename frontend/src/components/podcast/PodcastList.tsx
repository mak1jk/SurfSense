import React from 'react';
import { Box, Card, CardContent, Typography, IconButton, Grid, Chip } from '@mui/material';
import { PlayArrow, Delete, Download } from '@mui/icons-material';
import { Podcast } from '@/types/podcast';
import { formatDate } from '@/utils/date';

interface PodcastListProps {
  podcasts: Podcast[];
  onPlay: (podcast: Podcast) => void;
  onDelete: (podcast: Podcast) => void;
  onDownload: (podcast: Podcast) => void;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'completed':
      return 'success';
    case 'processing':
      return 'warning';
    case 'failed':
      return 'error';
    default:
      return 'default';
  }
};

export const PodcastList: React.FC<PodcastListProps> = ({
  podcasts,
  onPlay,
  onDelete,
  onDownload,
}) => {
  return (
    <Box>
      <Grid container spacing={2}>
        {podcasts.map((podcast) => (
          <Grid item xs={12} key={podcast.id}>
            <Card>
              <CardContent>
                <Box display="flex" justifyContent="space-between" alignItems="center">
                  <Box>
                    <Typography variant="h6">{podcast.title}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      Created {formatDate(podcast.created_at)}
                    </Typography>
                    <Box mt={1}>
                      <Chip
                        label={podcast.status}
                        color={getStatusColor(podcast.status)}
                        size="small"
                      />
                    </Box>
                  </Box>
                  <Box>
                    {podcast.is_completed && (
                      <>
                        <IconButton
                          color="primary"
                          onClick={() => onPlay(podcast)}
                          disabled={!podcast.file_location}
                        >
                          <PlayArrow />
                        </IconButton>
                        <IconButton
                          color="primary"
                          onClick={() => onDownload(podcast)}
                          disabled={!podcast.file_location}
                        >
                          <Download />
                        </IconButton>
                      </>
                    )}
                    <IconButton color="error" onClick={() => onDelete(podcast)}>
                      <Delete />
                    </IconButton>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
};
