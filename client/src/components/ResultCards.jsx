import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import ResultCard from "./ResultCard";
import "./ResultCards.css";

const container = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.06,
      delayChildren: 0.02,
    },
  },
};

const item = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.22 } },
  exit: { opacity: 0, y: -6, transition: { duration: 0.15 } },
};

const ResultCards = ({ results = [] }) => {
  if (!Array.isArray(results) || results.length === 0) return null;

  return (
    <section className="results-container" aria-label="Matched standards">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.div
          key="results-list"
          className="results-list"
          variants={container}
          initial="hidden"
          animate="show"
          exit="hidden"
          layout
        >
          {results.map((result, idx) => (
            <motion.div key={result.id} variants={item} layout>
              <ResultCard result={result} index={idx} />
            </motion.div>
          ))}
        </motion.div>
      </AnimatePresence>
    </section>
  );
};

export default ResultCards;