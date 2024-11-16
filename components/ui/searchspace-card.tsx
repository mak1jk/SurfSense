import { motion } from "framer-motion";

export function SearchSpaceCard({ searchSpace }: SearchSpaceCardProps) {
  const iconAnimation = {
    animate: {
      scale: [1, 1.2, 0.8, 1],
      rotate: [0, 180, 180, 0],
    },
    transition: {
      duration: 2,
      ease: "easeInOut",
      repeat: Infinity,
      repeatDelay: 1,
    },
  };

  return (
    <motion.div
      className="relative group"
      whileHover={{ scale: 1.05 }}
      transition={{ duration: 0.2 }}
    >
      <motion.div
        className="icon"
        animate={iconAnimation.animate}
        transition={iconAnimation.transition}
      >
        {/* contenuto dell'icona */}
      </motion.div>
      {/* resto del JSX */}
    </motion.div>
  );
} 