import Link from 'next/link';

export default function HomePage() {
  return (
    <main>
      <h1>LingoAI</h1>
      <p>Aprenda um novo idioma com um percurso guiado por IA, do nivelamento à prática diária.</p>
      <Link href="/register">Começar</Link>
    </main>
  );
}
