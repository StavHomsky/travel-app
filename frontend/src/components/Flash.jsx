export default function Flash({ message }) {
  if (!message) return null
  return <div className={`flash flash-${message.type}`} role="status">{message.text}</div>
}
