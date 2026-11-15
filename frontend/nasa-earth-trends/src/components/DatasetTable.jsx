const statusLabel = {
  ready: 'Ready',
  coming_soon: 'Coming soon',
}

function year(date) {
  return date ? String(date).slice(0, 4) : '—'
}

function DatasetTable({ items }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Variable</th>
            <th scope="col">Unit</th>
            <th scope="col">Period</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.dataset_id}>
              <th scope="row">
                {item.label}
                <small>{item.dataset_id}</small>
              </th>
              <td className="num">{item.unit}</td>
              <td className="num">
                {year(item.period_start)}–{year(item.period_end)}
              </td>
              <td>
                <span className={`status-pill status-${item.status}`}>
                  {statusLabel[item.status] || item.status}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export default DatasetTable
